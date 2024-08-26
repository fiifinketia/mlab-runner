# This Application will be used to to run machine learning models on the disal network of servrs  and will be able to run the models on the servers and get the results back to the main server through

# main.py
The selected code is a Python script that serves as a Runner for managing task environments and running tasks. It uses gRPC to communicate with clients and provides various methods for creating, stopping, and running tasks. The code also includes a function to check the worker count and raise an exception if there are not enough workers to create a task environment.

The code is organized into several classes and functions. The `Runner` class is the main class that serves as the gRPC server. It has several methods for handling tasks, such as `get_runner`, `stop_task`, `remove_task_environment`, `create_task_environment`, and `run_task`. The `Runner` class also includes static methods for managing worker counts and logging messages.

The `RunnerException` class is a custom exception class that is raised when there are not enough workers to create a task environment.

The `serve` function is an asynchronous function that starts the gRPC server, sets up the necessary services, and handles the server's lifecycle. It also starts the billing cron service and the pinggy server if enabled in the settings.

The code also includes a `settings` module that contains configuration settings for the Runner, such as the RPC URL, worker count, and whether to use the pinggy server.

Overall, the selected code is a comprehensive implementation of a Runner that can manage task environments and run tasks using gRPC.

# billing.py
The selected code is a Python script that contains a class named `BillingCronService`. This class is responsible for sending billing updates to a server at regular intervals. It uses the `schedule` library to run a function (`_submit_billing`) every 30 seconds.

The `BillingCronService` class has the following methods:

1. `__init__`: Initializes the class and sets up the billing API endpoint, retrieves server statistics, and schedules the billing update function.

2. `start`: Starts the billing update function in an infinite loop.

3. `stop`: Stops the billing update function.

4. `_get_server_stats`: Retrieves the current server statistics.

5. `_submit_billing`: Sends the billing update to the server by creating a `CheckBillDTO` object with the current server statistics and sending a POST request to the billing API endpoint.

The code also defines two enumerations (`Action` and `Any`) and two data transfer objects (`BalanceBillDTO` and `CheckBillDTO`). These are used to structure the data sent to the server for billing updates.

# cog.py
The selected code is a part of a Python script that is responsible for running cog commands. It contains several functions that are used to set up, prepare, and run cog jobs. Here is a brief explanation of the selected code:

1. `job_get_dirs`: This function takes a job ID, dataset name, and model name as input and returns the paths for the base directory, dataset directory, and model directory. It creates these directories if they do not exist.

2. `copyfile`: This function copies a file from the source path to the destination directory path. It raises an exception if an error occurs during the copying process.

3. `run`: This function runs a cog command using the `subprocess.Popen` function. It constructs a CLI script for training a cog model, including parameters for the dataset directory, base directory, result ID, API URL, user token, job ID, and an optional trained model path. It also includes a mount command to bind the base directory to a specific target directory in the cog environment.

4. `build_cli_script`: This function constructs a CLI script for training a cog model. It includes parameters for the dataset directory, base directory, task ID, user ID, job ID, and an optional trained model path. It also includes a mount command to bind the base directory to a specific target directory in the cog environment.

5. `run_process_with_std`: This function runs a process with standard input and output. It returns a subprocess object that can be used to read the process's output.

6. `fetch_results`: This function fetches the results of a cog job. It reads the result JSON files from the success and error directories and returns them as a tuple of strings and JSON objects.

7. `setup`: This function sets up the environment for a cog job. It clones the dataset and model repositories to a temporary directory and discards them after use. It also handles any exceptions that may occur during the cloning process.

8. `prepare`: This function prepares the environment for a cog job. If the dataset type is 'upload', it copies the dataset from the results directory to the dataset path. If the dataset type is 'default', it fetches the dataset from the specified branch of the dataset repository. It also fetches the model from the specified branch of the model repository.

9. `stop`: This function stops and removes all Docker containers that have the specified job ID as their ancestor. It uses the Docker CLI commands 'docker ps -a -q --filter ancestor={str(job_id)}' to get the list of container IDs, and then iterates over these IDs to stop and remove each container.

10. `remove`: This function removes the directories for the dataset and model associated with a job ID. It also removes the job ID directory itself.

11. `replace_source_with_destination`: This function replaces the source directory path with the destination directory path. It is used in the context of setting up a cog environment.

12. `change2_local_dir`: This function replaces the server base directory path with the results directory path. It is used to change the base directory path to a local directory path.


# git.py
The selected code is a Python class named `GitService` that provides methods for interacting with Git repositories. It uses the `gitlab` library to communicate with GitLab servers and the `git` library to interact with Git repositories.

The class has several methods for creating, cloning, deleting, and listing files in Git repositories. It also includes a custom `CloneProgress` class that updates the user about the progress of cloning operations.

The `GitService` class uses the `settings` module to access configuration variables such as the GitLab server URL and the GitLab token. It also includes a `format_repo_name` method that formats a repository name by appending "mlab-{type}" to it, where "{type}" is a string representing the type of the repository (e.g., "dataset" or "model").

The `check_exists` method checks if a repository with a given name and namespace exists on the GitLab server. If the repository exists, the method returns `True`; otherwise, it returns `False`.

The `clone_repo` method clones a repository from the GitLab server to a specified directory on the local machine. It first checks if the repository already exists in the specified directory, and if so, it clones the repository using the `clone_from` method. If the repository does not exist in the specified directory, the method raises a `RepoNotFoundError` exception.

The `delete_repo` method deletes a repository from the GitLab server. It first checks if the repository exists, and if so, it deletes the repository using the `delete_project` method of the `gitlab` library. If the repository does not exist, the method raises a `RepoNotFoundError` exception.

The `list_files` method lists the files in a Git repository. It first checks if the repository exists, and if so, it retrieves the repository's files using the `repository_tree` method of the `gitlab` library. If the repository does not exist, the method raises a `RepoNotFoundError` exception.

The `clone_from` method clones a repository from a specified URL to a specified directory on the local machine. It first configures the Git user's email and name, creates the specified directory if it does not exist, and then clones the repository using the `git clone` command. The method also allows the user to specify a branch to clone and a progress bar to display the progress of the cloning operation.

The `fetch` method fetches the latest changes from a remote repository to a local repository. It first checks if the repository exists, and if so, it fetches the latest changes using the `git pull` command. If the repository does not exist, the method raises a `RepoNotFoundError` exception.

The `stash` method stashes the changes in a local repository to a temporary location. It first checks if the repository exists, and if so, it stashes the changes using the `git stash` command.


# pinggy_helper.py

The selected code is a Python script that reads the pm2 logs file to get the latest pinggy URL and serves the information via HTTPS. It consists of two main classes: `PinggyHelper` and `PinggyHelperServer`.

The `PinggyHelper` class has three main methods:

1. `_read_pm2_logs_file(logs_dir: str) -> str`: This method reads the pm2 logs file and returns its content as a string.

2. `_get_latest_pinggy_urls() -> str | None`: This method reads the lines from the pm2 logs file from the bottom. It looks for a line that starts with "URLs:" and extracts the URLs from it. It then returns the URLs as a string, separated by commas. If no URLs are found, it returns `None`.

3. `do_GET(self)`: This method is a part of the `BaseHTTPRequestHandler` class and is called when a GET request is made to the server. It sends an HTTP response with a status code of 200 and a content type of "text/plain". It then writes the latest pinggy URL to the response body.

The `PinggyHelperServer` class has one main method:

1. `start_server()`: This method starts an HTTP server using the `HTTPServer` class from the `http.server` module. It sets the server to listen on the specified host and port, and it creates an instance of the `PinggyHelper` class to handle incoming requests. When the server is started, it prints a message indicating that the server has started. When the server is stopped (either by a `KeyboardInterrupt` or by calling `server_close()`), it prints a message indicating that the server has closed.

Overall, this code is designed to provide a simple HTTP server that reads the latest pinggy URL from the pm2 logs file and serves it to clients that make a GET request to the server.