# Third-Party Notices

The Drawback Engine **core** (`engine/drawback/{models,config,rules,matching,assumptions,defensibility,
estimate,serialize}` and `filing/`) uses the **Python standard library only** — no third-party runtime
dependencies. The components below are used by the API layer, the test suite, and the web frontend.

**All third-party components are permissive-licensed (MIT / BSD-3-Clause / Apache-2.0). There is no
copyleft (GPL/LGPL/AGPL) or weak-copyleft (MPL/EPL) dependency.** A proprietary distributor's only
obligations are attribution/notice retention (MIT/BSD) and, for Apache-2.0, retaining the NOTICE/patent
terms — satisfied by this file and `sbom.json`.

## Python (API + tests)
| Component | Version | License |
|---|---|---|
| fastapi | 0.111.0 | MIT |
| uvicorn | 0.30.1 | BSD-3-Clause |
| python-multipart | 0.0.9 | Apache-2.0 |
| pytest (test-only) | 8.2.2 | MIT |
| httpx (test-only) | 0.27.0 | BSD-3-Clause |

## JavaScript / TypeScript (web frontend)
| Component | Version | License |
|---|---|---|
| react, react-dom | 18.3.1 | MIT |
| @radix-ui/react-{dialog,dropdown-menu,popover,tabs,tooltip} | 1.x–2.x | MIT |
| @tanstack/react-table | 8.21.x | MIT |
| @tanstack/react-virtual | 3.13.x | MIT |
| recharts | 3.8.x | MIT |
| vite, @vitejs/plugin-react | 5.x / 4.x | MIT |
| typescript (dev) | 5.6.3 | Apache-2.0 |
| @types/react, @types/react-dom (dev) | 18.3.x | MIT |

## License texts
The full MIT, BSD-3-Clause, and Apache-2.0 license texts (and any upstream `NOTICE` files) ship with the
respective packages under `node_modules/<pkg>/LICENSE` and the Python package metadata. Retain those in
any distribution.

## Generating a complete transitive SBOM (before sale)
This file lists **direct** dependencies with verified licenses. For a complete transitive
software bill of materials, run a scanner against the lockfiles and confirm zero copyleft:

```bash
# JavaScript (full transitive tree)
cd web && npx license-checker --production --summary
# Python
pip install pip-licenses && pip-licenses --format=markdown
```

A machine-readable summary of the direct components is in `sbom.json` (CycloneDX-style).
