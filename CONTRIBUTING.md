# Contributing

Thanks for looking. This library is small on purpose.

## Rules of the road

- **Never invent a helper that writes facts from a model summary.** If you want a linter that *reads* text and refuses a write, that is in scope. Autowrite is not.
- Keep gates in `src/memory_ssot/gates.py`. New write paths must call them.
- Dummy examples only. No customer names, no real company data.
- File format is the API. If you change the markdown line shape, add a parse test.

## Dev setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check src tests examples
```

## PR checklist

- [ ] pytest green on 3.11+
- [ ] Quantity / commercial / action gates still fail closed
- [ ] README example still runs
- [ ] No secrets, no real company data

## License

By contributing you agree your changes are MIT, copyright assigned to the project (Juntae Kim / contributors).
