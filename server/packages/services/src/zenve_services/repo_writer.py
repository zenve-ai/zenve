from zenve_db.models import Project
from zenve_models.errors import NotFoundError, ValidationError
from zenve_utils.github import commit_tree, list_tree_paths

AGENT_BASE = ".zenve/agents"


def validate_relpath(relpath: str) -> str:
    """Guard against path traversal. Returns the normalized relative path."""
    normalized = relpath.lstrip("/")
    parts = normalized.split("/")
    depth = 0
    for part in parts:
        if part == "..":
            depth -= 1
        elif part and part != ".":
            depth += 1
        if depth < 0:
            raise ValidationError(f"Path traversal detected: {relpath!r}")
    return normalized


class RepoWriterService:
    def scaffold_agent(
        self,
        project: Project,
        agent_slug: str,
        rendered_files: dict[str, bytes],
        commit_message: str,
    ) -> str:
        """Commit an in-memory file tree under .zenve/agents/{agent_slug}/."""
        if not project.github_installation_id or not project.github_repo or not project.github_default_branch:
            raise ValidationError("Project has no GitHub repo connected")

        prefixed: dict[str, bytes | None] = {
            f"{AGENT_BASE}/{agent_slug}/{relpath}": content
            for relpath, content in rendered_files.items()
        }
        return commit_tree(
            project.github_installation_id,
            project.github_repo,
            project.github_default_branch,
            prefixed,
            commit_message,
        )

    def delete_agent(self, project: Project, agent_slug: str, commit_message: str) -> str:
        """Delete all files under .zenve/agents/{agent_slug}/ in one commit."""
        if not project.github_installation_id or not project.github_repo or not project.github_default_branch:
            raise ValidationError("Project has no GitHub repo connected")

        prefix = f"{AGENT_BASE}/{agent_slug}/"
        paths = list_tree_paths(
            project.github_installation_id,
            project.github_repo,
            prefix,
            ref=project.github_default_branch,
        )
        if not paths:
            raise NotFoundError(f"Agent '{agent_slug}' not found in repo")

        deletions: dict[str, bytes | None] = {p: None for p in paths}
        return commit_tree(
            project.github_installation_id,
            project.github_repo,
            project.github_default_branch,
            deletions,
            commit_message,
        )

    def scaffold_project(
        self,
        project: Project,
        files: dict[str, bytes | None],
        commit_message: str,
    ) -> str:
        """Commit an arbitrary set of full-path files in one GitHub commit."""
        if not project.github_installation_id or not project.github_repo or not project.github_default_branch:
            raise ValidationError("Project has no GitHub repo connected")
        return commit_tree(
            project.github_installation_id,
            project.github_repo,
            project.github_default_branch,
            files,
            commit_message,
        )

    def write_file(
        self,
        project: Project,
        agent_slug: str,
        relpath: str,
        content: bytes,
        commit_message: str,
    ) -> str:
        """Commit a single file under .zenve/agents/{agent_slug}/{relpath}."""
        if not project.github_installation_id or not project.github_repo or not project.github_default_branch:
            raise ValidationError("Project has no GitHub repo connected")

        safe_relpath = validate_relpath(relpath)
        path = f"{AGENT_BASE}/{agent_slug}/{safe_relpath}"
        return commit_tree(
            project.github_installation_id,
            project.github_repo,
            project.github_default_branch,
            {path: content},
            commit_message,
        )
