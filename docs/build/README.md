# Document builders

Node scripts (docx-js, pptxgenjs) that generate the Phase I document, the summary on research articles, the project report, the slides and the viva sheet from `results/*.json` and `results/figures/*.png`, so every number in the documents is the one the experiments produced.

```bash
cd docs/build && npm install docx pptxgenjs
BIQ_REPO=../.. DV_OUT=../project node phase1.js && node litsummary.js && node report.js && node slides.js && node viva.js
```
