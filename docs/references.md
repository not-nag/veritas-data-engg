# References

These sources informed the implementation and production notes. Reference ranges are not universal; population, measurement method, units, and context matter.

- [MedlinePlus hemoglobin](https://medlineplus.gov/ency/article/003645.htm): adult gender-specific fallback ranges and unit equivalents. Used only with explicit applicable demographics.
- [MedlinePlus RBC indices](https://medlineplus.gov/ency/article/003648.htm): MCV and MCHC fallback ranges.
- [MedlinePlus complete blood count](https://medlineplus.gov/lab-tests/complete-blood-count-cbc/): terminology and clinical context.
- [DailyMed acetaminophen](https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=acetaminophen): generic drug naming reference.
- [ESIC requisition training material](https://dmn.esic.gov.in/attachments/circularfile/Annexure_B_English_1758085846.pdf): an explicit Dolo 650 to paracetamol 650 mg mapping; used as a narrowly scoped prototype example, not a comprehensive medicine catalogue.
- [Sun Pharma India products](https://sunpharma.com/india-products/): Pantocid 20/40 formulation mapping; combination variants are not collapsed into this mapping.
- [Next.js route handlers](https://nextjs.org/docs/app/getting-started/route-handlers): local server-side proxy routes.
- [shadcn/ui manual installation](https://ui.shadcn.com/docs/installation/manual): locally owned UI primitives and neutral styling conventions.
- [Cloud Storage Pub/Sub notifications](https://cloud.google.com/storage/docs/pubsub-notifications): proposed event-driven production ingestion.
- [Cloud Run autoscaling](https://cloud.google.com/run/docs/about-instance-autoscaling): proposed worker scaling.
- [BigQuery MERGE](https://cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax#merge_statement): proposed deduplication during warehouse loading.

Local source documents: `Requirements/Assignment.docx`, the supplied ideal-schema CSV/XLSX, the clinical-name mapping workbook, and five original JSON files. Their inconsistencies are recorded in the assumptions document. The initial dictionary uses selected aliases rather than treating the supplied workbook as clinically validated ground truth.

- [MedlinePlus liver function tests](https://medlineplus.gov/lab-tests/liver-function-tests/): AST, ALT, ALP, and GGT terminology for aliases and named panel components.
- [British Columbia urinalysis guidance](https://www2.gov.bc.ca/assets/gov/health/practitioner-pro/bc-guidelines/urinalysis.pdf): terminology for nitrite, leukocyte esterase, urine microscopy, and specific gravity. No new universal numeric reference ranges were inferred from these terminology sources.

## Additional verified mappings and reference rules

- [GSK Ceftum label](https://india-pharma.gsk.com/media/k3xe5d1e/ceftum-tablets.pdf): cefuroxime axetil product strengths.
- [Intas products](https://www.intaspharma.com/products/): Ceftas and combination formulation distinctions.
- [Maldives Ministry of Health drug list](https://health.gov.mv/storage/uploads/lwZ95boy/wikvvaih.pdf): Azithral formulation evidence; historical formulation evidence does not establish current marketing approval.
- [Janssen Ultracet prescribing information](https://www.janssenlabels.com/package-insert/product-monograph/prescribing-information/ULTRACET-pi.pdf): tramadol/paracetamol combination.
- [Cipla signed pricing/formulation notice](https://apiv2.netmeds.com/images/NPPA_Pharma_pdf/Form-V-Apr-2025-Cipla.pdf): Emeset/ondansetron formulation evidence.
- [Abbott Duphalac](https://www.abbottbrasil.com.br/nossas-bulas/duphalac-lactulose.html): lactulose formulation.
- [MedlinePlus RBC count](https://medlineplus.gov/ency/article/003644.htm) and [creatinine](https://medlineplus.gov/ency/article/003475.htm): explicit adult gender-specific fallbacks.
- [MedlinePlus WBC count](https://medlineplus.gov/ency/article/003643.htm), [platelet count](https://medlineplus.gov/ency/article/003647.htm), [sodium](https://medlineplus.gov/ency/article/003481.htm), [potassium](https://medlineplus.gov/ency/article/003484.htm), and [phosphorus](https://medlineplus.gov/ency/article/003478.htm): limited adult, unit-specific fallbacks. Unknown age is not inferred.

Medicine normalisation retains formulation suffixes and strengths. Exact product evidence is linked from configuration and the inspector; ambiguous abbreviations are left unresolved. No universal titre cutoff is inferred from these references.

## Medicine and laboratory reference sources

Source verification date: 15 November 2026.

- [Alkem product catalogue](https://www.alkemlabs.com/our-offerings/rx-products) and [PAN-D product information](https://www.alkemlabs.com/pdf/adverse/PAN%20D.pdf): PAN 20/40 and combination ingredients; incomplete PAN is accepted only with an explicit injection form. Product strengths from reference material are not substituted into missing source doses.
- [NAFDAC Fortwin injection record](https://greenbook.nafdac.gov.ng/products/details/8301): ingredient/form evidence from a regulator entry for an Indian-manufactured product. This is formulation evidence, not a claim about the source report's exact pack or batch.
- [MedlinePlus blood differential](https://medlineplus.gov/ency/article/003657.htm): explicit-adult percentage reference examples; unknown/redacted age does not meet the configured adult rule.
- [University Hospitals laboratory reference ranges](https://www.uhhospitals.org/-/media/files/for-clinicians/research/lab-reference-ranges.pdf?hash=FE0D345C3ECEB8C338A09459498F9ED09D39EC95&la=en): RDW-CV interval listed for all ages.
- [UW Medicine A:G ratio test guide](https://testguide.labmed.uw.edu/view/AGR?tabs=no): interval across age/sex categories including unknown sex. These laboratory-specific examples require local laboratory validation and do not replace a supplied valid source range.

Extraction categories are engineering rules based on the supplied source labels, not clinical mappings. Contextual glucose recovery requires a urine-specific anchor plus the biochemical section heading and an explicitly qualitative result. Source rows, missing units, and numeric contradictions are preserved.

## Reference and medicine additions

Adult fallback intervals added on 16 November 2026 use MedlinePlus articles for [calcium](https://medlineplus.gov/ency/article/003477.htm), [chloride](https://medlineplus.gov/ency/article/003485.htm), [albumin](https://medlineplus.gov/ency/article/003480.htm), [total protein](https://medlineplus.gov/ency/article/003483.htm), [ALT](https://medlineplus.gov/ency/article/003473.htm), [AST](https://medlineplus.gov/ency/article/003472.htm), [bilirubin](https://medlineplus.gov/ency/article/003479.htm), [BUN](https://medlineplus.gov/ency/article/003474.htm) and sex-specific [MCH](https://medlineplus.gov/ency/article/003648.htm). Source ranges take priority, unknown ages do not receive these adult fallbacks, and missing or incompatible units remain invalid. These are published example intervals, not universal clinical cutoffs.

Additional exact product/form matches use [MCAZ's Dynapar inspection report](https://portal.mcaz.co.zw/?download_id=1830&sdm_process_download=1), [Troikaa's Dynapar AQ publication](https://www.troikaa.com/wp-content/uploads/2022/01/Dynapar-1-ml-ID-non-comparitive-clincal-study_IMJ.pdf), [Delhi State Cancer Institute's Econorm stock reference](https://dsci.delhi.gov.in/sites/default/files/dsci/circulars-orders/stock_of_edl_medicines_as_on_10mar2025.pdf), and the [Buscopan manufacturer leaflet](https://www.medicines.org.uk/emc/product/890/pil). Ingredient names are mapped; doses and missing strengths are never supplied by the dictionary.
