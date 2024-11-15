import nox

# 配置后端为 uv
nox.options.default_venv_backend = "uv"
nox.options.envdir = ".cache/noxs"
PYPROJECT = nox.project.load_toml("pyproject.toml")


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
def tests(session):
    session.install(*PYPROJECT["build-system"]["requires"])
    session.install(*PYPROJECT["project"]["dependencies"])
    session.install(*PYPROJECT["dependency-groups"]["dev"])
    session.install(".")
    session.run("pytest")
