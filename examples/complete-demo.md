# Complete synthetic demo

Upload `examples/complete-demo.json` through Reports → Upload reports → Choose files. All patient information is synthetic. Automatic Gemini mapping must be enabled with a working key and available quota. Do not approve HGB concentration as a dictionary alias before demonstrating the fallback; approved aliases take priority over Gemini.

The first upload creates **3 records** and suppresses **1 duplicate**. The file contains four report entries: two different lab reports, a discharge summary and an exact copy of that discharge summary.

## Demo A - Standardisation

Open the lab report named Demo A - Standardisation (synthetic). It should have no flags if Gemini resolves the label.

| Input | Demonstrates | Expected output |
| --- | --- | --- |
| TLC | Exact alias | White Blood Cell Count |
| Creatininee | Fuzzy spelling match | Creatinine, about 95% similarity |
| HGB concentration | Automatic Gemini fallback | Haemoglobin; source details say Gemini |
| Platelet count: 2.5 lac/cmm | Numeric unit conversion | 250000 cells/uL, reference 150000-450000 |
| Calcium: 9.5 mg/dL, no reference | Applicable adult fallback | Sourced reference; Within Range |
| BP: 110/70 mmHg | Composite decomposition | Separate systolic and diastolic observations |

The lab report has six input measurements and seven output observations. Inspect source details for matching and Reference source for provenance. Gemini responses may vary; failure or ambiguity remains unresolved rather than fabricated.

## Demo B - Review required

| Input | Expected classification |
| --- | --- |
| ALT: 91 U/L, reference 4-36 | Above Range |
| Albumin: 2.0 g/dL, reference 3.4-5.4 | Below Range |
| Hb: 999 g/dL | Outlier |
| TLC: 9700 g/dL | Invalid: incompatible unit |
| Creatinine: null | Invalid: missing result |
| ABSENT as test name | Unresolved; not sent to Gemini |

This report demonstrates genuine data problems separately from ordinary range deviations. Mark reviewed acknowledges inspection; it does not repair the data.

## Demo C - Medicines

Dolo 650 maps to Paracetamol; Pantocid 40 maps to Pantoprazole. Unverified Demo Brand stays unresolved. The discharge summary is flagged for medicine dictionary review.

## Finish

Inspect Needs review, inspect the raw/transformed report, check automatic decisions under More → AI mappings, export CSV, then view Activity. Re-uploading the unchanged file creates zero records and suppresses all four occurrences.

This valid file does not demonstrate malformed-file/dead-letter recovery or a second clinic schema. Those require separate inputs. The uploaded JSON wrapper contains clinicId and documentId; the report inspector's original JSON shows an individual report entry.
