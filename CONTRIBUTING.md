# Contributing

## Setup

```bash
git clone https://github.com/KnoxOps/agent-runbook.git
cd agent-runbook
pip install -e "."
```

## Running Tests

```bash
pytest agent_runbook/tests/ -q
```

## Creating a Pull Request

1. Fork the repo
2. Create a feature branch
3. Make changes, add tests
4. Run `pytest agent_runbook/tests/ -q` and ensure all pass
5. Open a PR against `master`
