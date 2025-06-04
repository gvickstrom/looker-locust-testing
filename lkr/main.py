import locust  # noqa
import os
import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, List, Optional
from lkr.utils.attribute_utils import process_attributes_with_cloud_storage
from lkr.cloud_storage import UserAttributesManager

import looker_sdk
import typer
from dotenv import load_dotenv

from lkr.load_test.locustfile_dashboard import DashboardUser
from lkr.load_test.embed_dashboard_observability.main import DashboardUserObservability
from lkr.load_test.locustfile_render import RenderUser
from lkr.utils.validate_api import validate_api_credentials

from lkr.load_test.locustfile_qid import QueryUser
from locust import events
from locust.env import Environment

import requests
import logging

app = typer.Typer(name="lkr", no_args_is_help=True)
state = {"client_id": False}

LOAD_TEST_PATH = pathlib.Path("lkr", "load_test")


class LoadTestType(str, Enum):
    dashboard = "dashboard"
    query = "query"
    render = "render"


class DebugType(str, Enum):
    looker = "looker"


@dataclass
class LookerApiCredentials:
    client_id: str
    client_secret: str
    base_url: str


@app.callback()
def main(
    ctx: typer.Context,
    env_file: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="Path to the environment file to load",
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
        ),
    ] = pathlib.Path(os.getcwd(), ".env"),
    client_id: Annotated[
        str,
        typer.Option(help="Looker API client ID"),
    ] = None,
    client_secret: Annotated[
        str,
        typer.Option(help="Looker API client secret"),
    ] = None,
    base_url: Annotated[
        str,
        typer.Option(help="Looker API base URL"),
    ] = None,
):
    # IP DETECTION CODE - runs at the start of every command
    print("=== CLOUD RUN ORIGIN DETECTION ===", flush=True)
    try:
        ip_response = requests.get('https://httpbin.org/ip', timeout=10)
        origin_ip = ip_response.json()['origin']
        print(f"Cloud Run job IP: {origin_ip}", flush=True)
        
        headers_response = requests.get('https://httpbin.org/headers', timeout=10)
        print(f"Request headers: {headers_response.json()}", flush=True)
        
    except Exception as e:
        print(f"Failed to get origin info: {e}", flush=True)
    
    print("=== END ORIGIN DETECTION ===", flush=True)
    
    # Rest of the existing callback code
    load_dotenv(dotenv_path=env_file, override=True)
    if ctx.invoked_subcommand in ["load-test", "load-test:query", "debug"]:
        validate_api_credentials(
            client_id=client_id, client_secret=client_secret, base_url=base_url
        )


@app.command()
def debug(
    type: Annotated[
        DebugType,
        typer.Argument(help="Type of debug to run (looker)"),
    ],
):
    """
    Check that the environment variables are set correctly
    """

    if type.value == "looker":
        typer.echo("Looking at the looker environment variables")
        if os.environ.get("LOOKERSDK_CLIENT_ID"):
            typer.echo(f"LOOKERSDK_CLIENT_ID: {os.environ.get('LOOKERSDK_CLIENT_ID')}")
        else:
            typer.echo("LOOKERSDK_CLIENT_ID: Not set")
        if os.environ.get("LOOKERSDK_CLIENT_SECRET"):
            typer.echo("LOOKERSDK_CLIENT_SECRET: *********")
        else:
            typer.echo("LOOKERSDK_CLIENT_SECRET: Not set")
        if os.environ.get("LOOKERSDK_BASE_URL"):
            typer.echo(f"LOOKERSDK_BASE_URL: {os.environ['LOOKERSDK_BASE_URL']}")
        else:
            typer.echo("LOOKERSDK_BASE_URL: Not set")
        
        # Enhanced CSV debugging
        typer.echo("\n=== CSV User Attributes Testing ===")
        if os.environ.get("BUCKET_NAME"):
            typer.echo(f"BUCKET_NAME: {os.environ.get('BUCKET_NAME')}")
            try:
                manager = UserAttributesManager(os.environ.get('BUCKET_NAME'))
                typer.echo(f"✅ CSV loaded successfully: {len(manager.user_attributes)} users")
                
                if manager.user_attributes:
                    # Show first 3 sample users
                    typer.echo("Sample user attributes from CSV:")
                    for i, user_data in enumerate(manager.user_attributes[:3]):
                        typer.echo(f"  User {i+1}: {user_data}")
                    
                    # Test the random selection
                    typer.echo("\nTesting random user selection:")
                    for i in range(3):
                        random_user = manager.get_random_user_attributes()
                        typer.echo(f"  Random user {i+1}: {random_user}")
                        
                    # Show available attribute names
                    if manager.user_attributes:
                        attr_names = list(manager.user_attributes[0].keys())
                        typer.echo(f"\nAvailable CSV columns: {attr_names}")
                else:
                    typer.echo("❌ No user data found in CSV")
                    
            except Exception as e:
                typer.echo(f"❌ Error loading CSV from cloud storage: {str(e)}")
        else:
            typer.echo("❌ BUCKET_NAME not set")
        
        typer.echo("\n=== Checking Looker Credentials ===")
        try:
            looker_client = looker_sdk.init40()
            response = looker_client.me()
            typer.echo(f"✅ Logged in as {response['first_name']} {response.last_name}")
        except Exception as e:
            typer.echo(f"❌ Error logging in to Looker: {str(e)}")


@app.command(name="load-test")
def load_test(
    users: Annotated[
        int, typer.Option(help="Number of users to run the test with", min=1, max=1000)
    ] = 25,
    spawn_rate: Annotated[
        float,
        typer.Option(help="Number of users to spawn per second", min=0, max=100),
    ] = 1,
    run_time: Annotated[
        int,
        typer.Option(help="How many minutes to run the load test for", min=1),
    ] = 5,
    dashboard: Annotated[
        str,
        typer.Option(
            help="Dashboard ID to run the test on. Keeps dashboard open for user, turn on auto-refresh to keep dashboard updated"
        ),
    ] = None,
    model: Annotated[
        List[str],
        typer.Option(
            help="Model to run the test on. Specify multiple models as --model model1 --model model2"
        ),
    ] = None,
    attribute: Annotated[
        List[str],
        typer.Option(
            help="Looker attributes to run the test on. Specify them as attribute:value like --attribute store:value. Excepts multiple arguments --attribute store:acme --attribute team:managers. Accepts random.randint(0,1000) format"
        ),
    ] = None,
    attribute_csv: Optional[str] = typer.Option(
        None, "--attribute-csv", help="Path to CSV file containing user attributes"
    ),
):
    # Process attributes from CSV and command line
    processed_attributes = process_attributes_with_cloud_storage(
        attribute, 
        attribute_csv, 
        os.environ.get('BUCKET_NAME')
    )

    # Add detailed logging about attributes
    typer.echo(f"\n🔍 Processed attributes for load test: {processed_attributes}")
    if processed_attributes:
        typer.echo(f"✅ {len(processed_attributes)} attributes will be assigned to users")
        for attr in processed_attributes:
            typer.echo(f"   - {attr}")
    else:
        typer.echo("⚠️  No attributes configured - users will have no context")
    typer.echo("")  # blank line

    from locust import events
    from locust.env import Environment

    """
    Run a load test on a dashboard or API query
    """
    if not (dashboard):
        raise typer.BadParameter("Either --dashboard or --qid must be provided")

    if not model:
        raise typer.BadParameter("At least one --model must be provided")

    typer.echo(
        f"Running load test with {users} users, {spawn_rate} spawn rate, and {run_time} minutes"
    )

    # Process attributes into the expected format

    class DashboardUserClass(DashboardUser):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Get random attributes for THIS user from CSV
            if os.environ.get('BUCKET_NAME'):
                try:
                    from lkr.cloud_storage import UserAttributesManager
                    manager = UserAttributesManager(os.environ.get('BUCKET_NAME'))
                    user_attrs = manager.get_random_user_attributes()
                    if user_attrs:
                        # Convert dict to list of "name:value" strings
                        self.attributes = [f"{k}:{v}" for k, v in user_attrs.items()]
                        print(f"DEBUG: User {self.user_id} got random attributes: {self.attributes}")
                    else:
                        self.attributes = []
                except Exception as e:
                    print(f"ERROR: Could not get random attributes: {e}")
                    self.attributes = []
            else:
                self.attributes = []
                
            self.dashboard = dashboard
            self.models = model

    env = Environment(
        user_classes=[DashboardUserClass],
        events=events,
    )
    runner = env.create_local_runner()
    
    runner.start(user_count=users, spawn_rate=spawn_rate)

    def quit_runner():
        runner.greenlet.kill()
        runner.quit()
        typer.Exit(1)

    runner.spawning_greenlet.spawn_later(run_time * 60, quit_runner)
    runner.greenlet.join()


@app.command(name="load-test:query")
def load_test_query(
    query: Annotated[
        List[str],
        typer.Option(help="Query ID (from explore url) to run the test on"),
    ],
    users: Annotated[
        int, typer.Option(help="Number of users to run the test with", min=1, max=1000)
    ] = 25,
    spawn_rate: Annotated[
        float,
        typer.Option(help="Number of users to spawn per second", min=0, max=100),
    ] = 1,
    run_time: Annotated[
        int,
        typer.Option(help="How many minutes to run the load test for", min=1),
    ] = 5,
    model: Annotated[
        List[str],
        typer.Option(
            help="Model to run the test on. Specify multiple models as --model model1 --model model2"
        ),
    ] = None,
    attribute: Annotated[
        List[str],
        typer.Option(
            help="Looker attributes to run the test on. Specify them as attribute:value like --attribute store:value. Excepts multiple arguments --attribute store:acme --attribute team:managers. Accepts random.randint(0,1000) format"
        ),
    ] = [],
    attribute_csv: Optional[str] = typer.Option(
        None, "--attribute-csv", help="Path to CSV file containing user attributes"
    ),
    wait_time_min: Annotated[
        int,
        typer.Option(
            help="User tasks have a random wait time between this and the max wait time",
            min=1,
            max=100,
        ),
    ] = 1,
    wait_time_max: Annotated[
        int,
        typer.Option(
            help="User tasks have a random wait time between this and the min wait time",
            min=1,
            max=100,
        ),
    ] = 15,
    sticky_sessions: Annotated[
        bool,
        typer.Option(
            help="Keep the same user logged in for the duration of the test. sticky_sessions=True is currently not supported with the Looker SDKs, we are working around it in the User class."
        ),
    ] = False,
    query_async: Annotated[
        bool, typer.Option(help="Run the query asynchronously")
    ] = False,
    async_bail_out: Annotated[
        int,
        typer.Option(
            help="How many iterations to wait for the async query to complete (roughly number of seconds)"
        ),
    ] = 120,
):
    # Process attributes from CSV and command line
    processed_attributes = process_attributes_with_cloud_storage(
        attribute, 
        attribute_csv, 
        os.environ.get('BUCKET_NAME')
    )
    
    # Add detailed logging about attributes
    typer.echo(f"\n🔍 Processed attributes for query load test: {processed_attributes}")
    if processed_attributes:
        typer.echo(f"✅ {len(processed_attributes)} attributes will be assigned to users")
        for attr in processed_attributes:
            typer.echo(f"   - {attr}")
    else:
        typer.echo("⚠️  No attributes configured - users will have no context")
    typer.echo("")  # blank line
    
    if not query:
        raise typer.BadParameter("At least one --query must be provided")
    if not model:
        raise typer.BadParameter("At least one --model must be provided")
    from locust import between

    class QueryUserClass(QueryUser):
        wait_time = between(wait_time_min, wait_time_max)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.attributes = processed_attributes  # Use processed attributes
            self.qid = query
            self.models = model
            self.result_format = "json_bi"
            self.query_async = query_async
            self.async_bail_out = async_bail_out
            self.sticky_sessions = sticky_sessions

    from locust import events
    from locust.env import Environment

    env = Environment(
        user_classes=[QueryUserClass],
        events=events,
    )
    runner = env.create_local_runner()

    # gevent.spawn(stats_printer(env.stats))
    runner.start(user_count=users, spawn_rate=spawn_rate)

    def quit_runner():
        runner.greenlet.kill()
        runner.quit()
        typer.Exit(1)

    runner.spawning_greenlet.spawn_later(run_time * 60, quit_runner)
    runner.greenlet.join()


@app.command(name="load-test:render")
def load_test_render(
    dashboard: Annotated[
        str,
        typer.Option(
            help="Dashboard ID to render",
        ),
    ],
    users: Annotated[
        int, typer.Option(help="Number of users to run the test with", min=1, max=1000)
    ] = 25,
    spawn_rate: Annotated[
        float,
        typer.Option(help="Number of users to spawn per second", min=0, max=100),
    ] = 1,
    run_time: Annotated[
        int,
        typer.Option(help="How many minutes to run the load test for", min=1),
    ] = 5,
    model: Annotated[
        List[str],
        typer.Option(
            help="Model to run the test on. Specify multiple models as --model model1 --model model2"
        ),
    ] = None,
    attribute: Annotated[
        List[str],
        typer.Option(
            help="Looker attributes to run the test on. Specify them as attribute:value like --attribute store:value. Excepts multiple arguments --attribute store:acme --attribute team:managers. Accepts random.randint(0,1000) format"
        ),
    ] = [],
    attribute_csv: Optional[str] = typer.Option(
        None, "--attribute-csv", help="Path to CSV file containing user attributes"
    ),
    result_format: Annotated[
        str,
        typer.Option(
            help="Format of the rendered output (pdf, png, jpg)",
        ),
    ] = "pdf",
    render_bail_out: Annotated[
        int,
        typer.Option(
            help="How many iterations to wait for the render task to complete (roughly number of seconds)"
        ),
    ] = 120,
    run_once: Annotated[
        bool,
        typer.Option(
            help="Make each user run its render task only once.", show_default=True
        ),
    ] = False,
):
    # Process attributes from CSV and command line
    processed_attributes = process_attributes_with_cloud_storage(
        attribute, 
        attribute_csv, 
        os.environ.get('BUCKET_NAME')
    )
    
    # Add detailed logging about attributes
    typer.echo(f"\n🔍 Processed attributes for render load test: {processed_attributes}")
    if processed_attributes:
        typer.echo(f"✅ {len(processed_attributes)} attributes will be assigned to users")
        for attr in processed_attributes:
            typer.echo(f"   - {attr}")
    else:
        typer.echo("⚠️  No attributes configured - users will have no context")
    typer.echo("")  # blank line
    
    if not dashboard:
        raise typer.BadParameter("--dashboard must be provided")
    if not model:
        raise typer.BadParameter("At least one --model must be provided")
    from locust import between

    class RenderUserClass(RenderUser):
        wait_time = between(1, 15)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.attributes = processed_attributes  # Use processed attributes 
            self.dashboard = dashboard
            self.models = model
            self.result_format = result_format
            self.render_bail_out = render_bail_out
            self.run_once = run_once  # Pass the command-line flag value

    from locust import events
    from locust.env import Environment

    env = Environment(
        user_classes=[RenderUserClass],
        events=events,
    )
    runner = env.create_local_runner()

    runner.start(user_count=users, spawn_rate=spawn_rate)

    def quit_runner():
        runner.greenlet.kill()
        runner.quit()
        typer.Exit(1)

    runner.spawning_greenlet.spawn_later(run_time * 60, quit_runner)
    runner.greenlet.join()

@app.command(name="load-test:embed-observability")
def load_test_embed_observability(
    dashboard: Annotated[
        str,
        typer.Option(
            help="Dashboard ID to render",
        ),
    ],
    users: Annotated[
        int, typer.Option(help="Number of users to run the test with", min=1, max=1000)
    ] = 5,
    spawn_rate: Annotated[
        float,
        typer.Option(help="Number of users to spawn per second", min=0, max=100),
    ] = 1,
    run_time: Annotated[
        int,
        typer.Option(help="How many minutes to run the load test for", min=1),
    ] = 5,
    port: Annotated[
        int,
        typer.Option(
            help="Port to run the embed server on",
        ),
    ] = 4000,
    min_wait: Annotated[
        int,
        typer.Option(help="Minimum wait time between tasks", min=1),
    ] = 60,
    max_wait: Annotated[
        int,
        typer.Option(help="Maximum wait time between tasks", min=1),
    ] = 120,
    model: Annotated[
        List[str],
        typer.Option(
            help="Model to run the test on. Specify multiple models as --model model1 --model model2"
        ),
    ] = None,
    completion_timeout: Annotated[
        int,
        typer.Option(help="Timeout in seconds for the dashboard run complete event", min=1),
    ] = 120,
    attribute: Annotated[
        List[str],
        typer.Option(
            help="Looker attributes to run the test on. Specify them as attribute:value like --attribute store:value. Excepts multiple arguments --attribute store:acme --attribute team:managers. Accepts random.randint(0,1000) format"
        ),
    ] = [],
    attribute_csv: Optional[str] = typer.Option(
        None, "--attribute-csv", help="Path to CSV file containing user attributes"
    ),
    log_event_prefix: Annotated[
        str,
        typer.Option(
            help="Prefix to add to the log event",
        ),
    ] = "looker-embed-observability",
    do_not_open_url: Annotated[
        bool,
        typer.Option(
            help="Do not open the URL in the observability browser, useful for viewing a user's embed dashboard when running locally",
        ),
    ] = False
    
):
    """
    \b
    Open dashboards with observability metrics. The metrics are collected through Looker's JavaScript events and logged with the specified prefix. This command will:
    1. Start an embed server to host the dashboard iframe
    2. Spawn multiple users that will:
       - Open the dashboard in an iframe
       - Wait for the dashboard to load
       - Track timing metrics for:
         - dashboard:loaded - Dashboard load time
         - dashboard:run:start - Query start time
         - dashboard:run:complete - Query completion time
         - dashboard:tile:start - Individual tile start time
         - dashboard:tile:complete - Individual tile completion time
    3. Will also track start and end times for the whole process (looker_embed_task_start and looker_embed_task_complete)
    4. Log all events with timing information to help analyze performance in a JSON format.  Events begin with <log_event_prefix>:*
    5. Automatically stop after the specified run time
    
    \f
    """
    # Process attributes from CSV and command line
    processed_attributes = process_attributes_with_cloud_storage(
        attribute, 
        attribute_csv, 
        os.environ.get('BUCKET_NAME')
    )
    
    # Add detailed logging about attributes
    typer.echo(f"\n🔍 Processed attributes for embed observability test: {processed_attributes}")
    if processed_attributes:
        typer.echo(f"✅ {len(processed_attributes)} attributes will be assigned to users")
        for attr in processed_attributes:
            typer.echo(f"   - {attr}")
    else:
        typer.echo("⚠️  No attributes configured - users will have no context")
    typer.echo("")  # blank line
    
    import threading

    from lkr.load_test.embed_dashboard_observability.embed_server import run_server
        # Start the embed server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True, args=(port,log_event_prefix))
    server_thread.start()

    class EmbedDashboardUserClass(DashboardUserObservability):
        wait_time = locust.between(min_wait, max_wait)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.attributes = processed_attributes  # Use processed attributes
            self.dashboard = dashboard
            self.models = model
            self.completion_timeout = completion_timeout
            self.embed_domain = f"http://localhost:{port}"
            self.log_event_prefix = log_event_prefix
            self.do_not_open_url = do_not_open_url
            
    env = Environment(
        user_classes=[EmbedDashboardUserClass],
        events=events,
    )
    runner = env.create_local_runner()

    runner.start(user_count=users, spawn_rate=spawn_rate)


    def quit_runner():
        runner.greenlet.kill()
        runner.quit()
        server_thread.join(timeout=1)
        if server_thread.is_alive():
            server_thread._stop()
        typer.Exit(1)

    runner.spawning_greenlet.spawn_later(run_time * 60, quit_runner)
    runner.greenlet.join()


if __name__ == "__main__":
    app()