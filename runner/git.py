"""A service for interacting with git repositories."""
import logging
import os
from typing import Any, Dict
from git import List, Repo, RemoteProgress
from gitlab import Gitlab
from runner.settings import settings

class CloneProgress(RemoteProgress):
    _logger = logging.getLogger(__name__)
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            self._logger.info(message)
class RepoNotFoundError(Exception):
    """Raised when a repository is not found."""
    pass

class ClonePathExistsError(Exception):
    """Raised when a path to clone a repository already exists."""
    pass

class RepoTypes:
    """Types of repositories."""
    DATASET = "dataset"
    MODEL = "model"
class GitService:
    """A service for interacting with git repositories."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.gl = Gitlab(url=settings.gitlab_url, private_token=settings.gitlab_token)

    def get_project(self, repo_name_with_namespace: str) -> Any:
        """Get a project."""
        return self.gl.projects.get(repo_name_with_namespace)

    def create_repo(self, repo_name: str, repo_type: str, username: str, is_private: bool, group_id: str | None = None) -> tuple[str, str]:
        """Create a repository."""
        repo_name = self.format_repo_name(repo_name=repo_name, repo_type=repo_type)
        namespace_id = group_id if group_id is not None else username
        if not self.check_exists(repo_name=repo_name, namespace=namespace_id):
            self.gl.auth()

            user = self.gl.users.list(search=username)[0]
            project = user.projects.create(
                {
                    "name": repo_name,
                    "visibility": "private" if is_private else "internal",
                    "namespace_id": group_id,
                }
            )
            repo_with_namespace = f"{username if group_id is None else group_id}/{repo_name}"
            return (repo_with_namespace, project.ssh_url_to_repo)
        else:
            raise RepoNotFoundError(f"Repository '{repo_name}' already exists.")

    def clone_repo(self, repo_name_with_namspace: str, to: str, branch: str | None = None) -> None:
        """Clone a repository."""
        # check if the repository has been cloned already
        if self.check_exists(repo_name=repo_name_with_namspace):
            repo_git_url = self.make_clone_url(repo_with_namespace=repo_name_with_namspace)
            # allow all users to make changes to directory
            self.clone_from(url=repo_git_url, to_path=to, branch=branch if branch is not None else "main")
        else:
            raise RepoNotFoundError(f"Repository '{repo_name_with_namspace}' does not exist.")

    def delete_repo(self, repo_name_with_namespace: str) -> None:
        """Delete a repository."""
        if self.check_exists(repo_name=repo_name_with_namespace):
            project = self.gl.projects.get(repo_name_with_namespace)
            project.delete()
        else:
            raise RepoNotFoundError(f"Repository '{repo_name_with_namespace}' does not exist.")

    def format_repo_name(self, repo_name: str, repo_type: str) -> str:
        """Format a repository name."""
        git_name = self.make_git_name(repo_name)
        # APPEND mlab-{type} to the name.
        return f"{repo_type}-{git_name}"


    def make_git_name(self, name: str) -> str:
        """Make a git name."""
        # use all lower case, replace any spaces with hyphens, and append ".git" to the name.
        return name.lower().replace(" ", "-")

    def list_files(self, repo_name_with_namespace: str) -> Any | List[Dict[str, Any]]:
        """list files from a git repository."""
        if self.check_exists(repo_name=repo_name_with_namespace):
            repo = self.gl.projects.get(repo_name_with_namespace)
            files = repo.repository_tree(all=True)
            return files
        else:
            raise RepoNotFoundError(f"Repository '{repo_name_with_namespace}' does not exist.")

    def check_exists(self, repo_name: str, namespace: str | None = None) -> bool:
        """Check if a repository exists."""
        self.gl.auth()
        try:
            project_with_namespace = repo_name if namespace is None else f"{namespace}/{repo_name}"
            project = self.gl.projects.get(project_with_namespace)
            return True if project is not None else False
        except Exception:
            return False
    def make_clone_url(self, repo_with_namespace: str) -> str:
        """Make a clone url."""
        return f"ssh://git@{settings.gitlab_server}:2424/{repo_with_namespace}.git"

    def clone_from(self, url: str, to_path: str, branch: str | None = None, env: dict[str, str] | None = None, progress: RemoteProgress | None = None) -> None:
        """Clone a repository."""
        os.system(f"git config --global user.email disal@admin.git")
        os.system(f"git config --global user.name disal")
        os.makedirs(to_path, exist_ok=True)
        os.chmod(to_path, 0o777)
        os.system(f"ssh-keyscan -t rsa {settings.gitlab_server} >> ~/.ssh/known_hosts")
        run_script = f"GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no'  git clone {url} {to_path}/."
        if branch is not None and len(branch) > 0:
            run_script += f" --branch {branch}"
        run_script += " --progress"
        os.system(run_script)

    def fetch(self, repo_name_with_namspace: str, to: str, branch: str | None = None) -> None:
        """Clone a repository."""
        # check if the repository has been cloned already
        self.stash(repo_name_with_namspace=repo_name_with_namspace, to=to)
        if self.check_exists(repo_name=repo_name_with_namspace):
            os.system(f"git config --global user.email disal@admin.git")
            os.system(f"git config --global user.name disal")
            os.chdir(to)
            os.system(f"GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no' git pull origin {branch if branch is not None else 'main'}")
        else:
            raise RepoNotFoundError(f"Repository '{repo_name_with_namspace}' does not exist.")

    def stash(self, repo_name_with_namspace: str, to: str) -> None:
        """Clone a repository."""
        # check if the repository has been cloned already
        if self.check_exists(repo_name=repo_name_with_namspace):
            os.system(f"git config --global user.email disal@admin.git")
            os.system(f"git config --global user.name disal")
            os.chdir(to)
            os.system("git stash")
