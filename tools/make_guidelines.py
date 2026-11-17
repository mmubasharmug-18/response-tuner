from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "guidelines"
NOTE = "Example guideline for training use only. Not medical advice."

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, spaceAfter=7)
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=25, spaceAfter=4)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=10, spaceAfter=5)
H3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11.5, leading=15, spaceBefore=6, spaceAfter=4)
SMALL = ParagraphStyle("small", fontName="Helvetica-Oblique", fontSize=9, leading=12, spaceAfter=8, textColor=colors.HexColor("#555555"))
ITEM = ParagraphStyle("item", parent=BODY, leftIndent=16, bulletIndent=4, spaceAfter=3)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=9.5, leading=12)
CELL_HEAD = ParagraphStyle("cellhead", fontName="Helvetica-Bold", fontSize=9.5, leading=12)

GUIDES = {}

GUIDES["adult_hypertension_guideline.pdf"] = {
    "title": "Adult Hypertension Guideline (Example)",
    "short": "Adult Hypertension Guideline",
    "subject": "Hypertension",
    "pages": [
        [
            ("h2", "1. Purpose and scope"),
            ("p", "This guideline explains how adults aged 18 and over with raised blood pressure are diagnosed and treated in primary care. It does not cover pregnancy or children."),
            ("h2", "2. Diagnosis"),
            ("h3", "2.1 Measuring blood pressure"),
            ("p", "Measure blood pressure with the patient seated and rested for five minutes, with the arm supported at heart level. Take two readings one minute apart and record the lower one. If the two readings differ by more than 10 mmHg, take a third. Use a cuff that fits the upper arm."),
            ("h3", "2.2 Confirming the diagnosis"),
            ("p", "A clinic reading of 140/90 mmHg or higher should be confirmed with home or ambulatory monitoring. Hypertension is confirmed when the daytime average on ambulatory monitoring is 135/85 mmHg or higher, or when the average of home readings is 135/85 mmHg or higher."),
        ],
        [
            ("h3", "2.3 Urgent assessment"),
            ("p", "A clinic reading of 180/120 mmHg or higher needs same-day assessment if the patient has symptoms such as chest pain, severe headache, confusion, vision changes or signs of heart failure. Without symptoms, repeat the test within seven days."),
            ("h2", "3. Lifestyle advice"),
            ("p", "Offer lifestyle advice at diagnosis and at every review."),
            ("bullets", [
                "Keep salt intake below 6 g a day.",
                "Do at least 150 minutes of moderate exercise each week.",
                "Keep alcohol within the national limit.",
                "Stop smoking and offer help to do so.",
                "Aim for a healthy body weight.",
            ]),
            ("h2", "4. Medicines"),
            ("p", "Start medicine when lifestyle changes are not enough, or straight away for stage 2 hypertension or high cardiovascular risk. Choose the first medicine using the table on the next page."),
        ],
        [
            ("h3", "4.1 First choice of medicine"),
            ("table", [
                ["Patient group", "First choice", "Notes"],
                ["Under 55, not Black African or Caribbean", "ACE inhibitor or ARB", "Check kidney function and potassium before starting"],
                ["55 or older, or Black African or Caribbean", "Calcium channel blocker", "Watch for ankle swelling"],
                ["Type 2 diabetes at any age", "ACE inhibitor or ARB", "Check kidney function and potassium before starting"],
            ]),
            ("p", "If an ACE inhibitor causes a persistent dry cough, switch to an ARB."),
            ("h3", "4.2 Adding more medicines"),
            ("p", "If blood pressure stays above target on one medicine, add a second from a different group. If it is still above target on two medicines, use all three: an ACE inhibitor or ARB, a calcium channel blocker and a thiazide-like diuretic. For resistant hypertension on three medicines, consider adding low-dose spironolactone if potassium is 4.5 mmol/L or lower, and seek specialist advice."),
        ],
        [
            ("h2", "5. Targets"),
            ("p", "Aim for a clinic reading below 140/90 mmHg in people under 80, and below 150/90 mmHg in people aged 80 or over."),
            ("h2", "6. Follow-up"),
            ("p", "Review four weeks after starting or changing a medicine. Once blood pressure is controlled, review every six months. Check kidney function, potassium and cholesterol once a year. Review the full medicine list at every visit."),
            ("h2", "7. Medicines to use with care"),
            ("p", "NSAIDs such as ibuprofen can raise blood pressure. Together with an ACE inhibitor and a diuretic they can harm the kidneys. Ask patients to check with a pharmacist before taking them."),
        ],
    ],
}

GUIDES["type2_diabetes_guideline.pdf"] = {
    "title": "Type 2 Diabetes Management Guideline (Example)",
    "short": "Type 2 Diabetes Guideline",
    "subject": "Type 2 diabetes",
    "pages": [
        [
            ("h2", "1. Purpose and scope"),
            ("p", "This guideline covers the diagnosis and routine care of adults with type 2 diabetes in primary care. It does not cover type 1 diabetes or diabetes in pregnancy."),
            ("h2", "2. Diagnosis"),
            ("p", "Type 2 diabetes is diagnosed when HbA1c is 48 mmol/mol (6.5%) or higher, or when fasting plasma glucose is 7.0 mmol/L or higher. In a person without symptoms, repeat the test to confirm. In a person with typical symptoms, one raised result is enough."),
            ("h3", "2.1 Prediabetes"),
            ("p", "An HbA1c of 42 to 47 mmol/mol (6.0 to 6.4%) suggests a high risk of developing diabetes. Offer a lifestyle programme and check HbA1c once a year."),
        ],
        [
            ("h2", "3. Targets"),
            ("p", "Agree an HbA1c target with each person. The usual targets are shown below."),
            ("table", [
                ["Situation", "HbA1c target"],
                ["Lifestyle or metformin alone", "48 mmol/mol (6.5%)"],
                ["On medicines that can cause low blood sugar", "53 mmol/mol (7.0%)"],
                ["Older or frail people", "58 mmol/mol (7.5%) or looser"],
            ]),
            ("h2", "4. Medicines"),
            ("h3", "4.1 First choice"),
            ("p", "Offer metformin as the first medicine. Start at a low dose with food and increase slowly to reduce stomach upset. Do not start metformin if eGFR is below 30 mL/min/1.73m2, and review the dose if eGFR is below 45."),
        ],
        [
            ("h3", "4.2 Adding a second medicine"),
            ("p", "If HbA1c is not at target on metformin, add a second medicine. For people with heart failure or established heart disease, add an SGLT2 inhibitor. Warn people taking an SGLT2 inhibitor about genital thrush, and tell them to stop it during an illness with vomiting or poor fluid intake."),
            ("h2", "5. Low blood sugar"),
            ("p", "Low blood sugar (hypoglycaemia) means a blood glucose below 4 mmol/L. Symptoms include shaking, sweating, hunger, confusion and headache."),
            ("h3", "5.1 Treatment"),
            ("p", "If the person is awake and can swallow, give 15 to 20 g of fast-acting carbohydrate, such as 150 to 200 mL of fruit juice or 4 to 5 glucose tablets. Recheck glucose after 10 to 15 minutes and repeat if it is still below 4 mmol/L. Follow with a snack or meal. If the person cannot swallow or is unconscious, call emergency services."),
        ],
        [
            ("h2", "6. Yearly review"),
            ("p", "Offer every adult with type 2 diabetes a review once a year. It should include:"),
            ("bullets", [
                "A foot check for loss of feeling, pulses and skin damage.",
                "Eye screening for diabetic retinopathy.",
                "A kidney check with eGFR and urine albumin-to-creatinine ratio.",
                "A blood pressure and cholesterol check.",
                "A review of medicines, weight and smoking.",
            ]),
            ("h2", "7. Sick day rules"),
            ("p", "During an illness with vomiting, diarrhoea or fever, pause metformin, SGLT2 inhibitors, ACE inhibitors and diuretics. Restart them once the person is eating and drinking normally again, usually after 24 to 48 hours. Keep checking blood glucose and keep drinking fluids."),
            ("h2", "8. When to refer"),
            ("p", "Refer urgently for a foot ulcer or signs of foot infection. Ask for specialist advice if HbA1c stays above target on three medicines."),
        ],
    ],
}

GUIDES["asthma_adult_guideline.pdf"] = {
    "title": "Asthma Management Guideline for Adults (Example)",
    "short": "Adult Asthma Guideline",
    "subject": "Asthma",
    "pages": [
        [
            ("h2", "1. Purpose and scope"),
            ("p", "This guideline covers the diagnosis and long-term management of asthma in adults. Treatment of children is not covered."),
            ("h2", "2. Diagnosis"),
            ("p", "Suspect asthma in adults with wheeze, cough, chest tightness or breathlessness that is worse at night or in the early morning, or that comes on with exercise, cold air or allergens. Confirm with spirometry that shows reversible airflow limitation. Peak flow that varies by more than 20% over two weeks also supports the diagnosis."),
            ("h2", "3. Treatment steps"),
            ("table", [
                ["Step", "Treatment"],
                ["Step 1", "Reliever inhaler (salbutamol) when needed"],
                ["Step 2", "Add a low-dose inhaled steroid preventer, taken every day"],
                ["Step 3", "Add a long-acting reliever to the preventer"],
                ["Step 4", "Raise the steroid dose or add another medicine, with specialist advice"],
            ]),
        ],
        [
            ("h2", "4. Inhaler use"),
            ("p", "Check inhaler technique at every review and after any change of device. Use a spacer with a pressurised metered-dose inhaler. Rinse the mouth after using an inhaled steroid to reduce the risk of oral thrush."),
            ("h2", "5. Self-management"),
            ("p", "Every patient should have a written asthma action plan. Teach patients with poor control to measure peak flow, and to act when it drops below 80% of their best. Common triggers are cold air, exercise, dust mites, pollen, smoke and chest infections."),
            ("h2", "6. Reviews"),
            ("p", "Review at least once a year. Ask about waking at night, reliever use and days lost from work. Using a reliever inhaler more than three times a week suggests poor control and a need to step up treatment."),
        ],
        [
            ("h2", "7. Severe attack"),
            ("h3", "7.1 Signs of a severe attack"),
            ("p", "A severe attack is likely when the person cannot complete a sentence in one breath, breathes more than 25 times a minute, has a heart rate above 110 beats a minute, or has a peak flow of 33 to 50% of their best."),
            ("h3", "7.2 Life-threatening signs"),
            ("p", "A silent chest, blue lips, exhaustion, confusion or a peak flow below 33% of best are life-threatening. Call emergency services. While waiting, give oxygen if available and a high-dose reliever through a spacer."),
            ("h2", "8. Medicines to avoid"),
            ("p", "Beta blockers can trigger severe asthma and should be avoided. Ask about aspirin or NSAID sensitivity before prescribing these medicines."),
        ],
    ],
}

GUIDES["common_infections_guideline.pdf"] = {
    "title": "Common Infections and Antibiotic Use (Example)",
    "short": "Common Infections Guideline",
    "subject": "Infections and antibiotics",
    "pages": [
        [
            ("h2", "1. Purpose"),
            ("p", "This guideline helps clinicians use antibiotics only when they are needed. Most coughs, colds and sore throats are caused by viruses and do not need antibiotics."),
            ("h2", "2. Sore throat"),
            ("p", "Most sore throats get better within a week without antibiotics. Use the FeverPAIN score: fever in the last 24 hours, pus on the tonsils, attending within three days of onset, severely inflamed tonsils, and no cough or cold symptoms. A score of 0 or 1 means antibiotics are not needed. A score of 2 or 3 suggests a delayed prescription. A score of 4 or more may justify an antibiotic. Advise paracetamol or ibuprofen for pain."),
        ],
        [
            ("h2", "3. Urinary tract infection in women"),
            ("p", "For an uncomplicated infection in a non-pregnant woman with burning on passing urine and frequent urination, treat with nitrofurantoin 100 mg modified-release twice a day for three days if eGFR is 45 or above. Trimethoprim for three days is an alternative if local resistance is low. Send a urine sample if the woman is pregnant, if symptoms persist, or if there are signs of kidney infection such as fever or loin pain."),
            ("h2", "4. Community-acquired pneumonia"),
            ("p", "Assess severity with the CRB-65 score: confusion, respiratory rate of 30 or more, low blood pressure, and age 65 or over. A score of 0 suggests home treatment. A score of 1 or 2 needs hospital assessment. A score of 3 or 4 is high risk and needs urgent admission. For low-severity pneumonia treated at home, use amoxicillin 500 mg three times a day for five days."),
        ],
        [
            ("h2", "5. Penicillin allergy"),
            ("p", "Ask what happened, when it happened and how soon after the first dose. A mild rash does not always mean a true allergy. For a confirmed allergy, use doxycycline or clarithromycin instead in respiratory infections. Record the reaction in the notes."),
            ("h2", "6. Preventing infection"),
            ("p", "Wash hands with soap and water for at least 20 seconds. Cover coughs and sneezes. Offer a yearly flu vaccine to adults aged 65 and over and to people with long-term conditions such as asthma and diabetes."),
            ("h2", "7. Red flags"),
            ("p", "A high temperature with a stiff neck, a rash that does not fade when pressed, or sudden confusion needs emergency assessment. Do not delay for tests."),
            ("h2", "8. Advice for patients"),
            ("p", "Take the course exactly as prescribed. Do not save tablets or share them. Antibiotics do not work against viruses such as colds and flu."),
        ],
    ],
}

GUIDES["medicine_safety_guideline.pdf"] = {
    "title": "Safe Use of Common Medicines (Example)",
    "short": "Safe Use of Medicines",
    "subject": "Medicine safety",
    "pages": [
        [
            ("h2", "1. Purpose"),
            ("p", "This guideline gives short safety advice for medicines that many adults use at home."),
            ("h2", "2. Paracetamol"),
            ("p", "In adults over 50 kg the usual dose is 1 g every four to six hours, with a maximum of 4 g in 24 hours. Adults under 50 kg or with liver disease need a lower daily maximum, so ask a pharmacist. Check other products for hidden paracetamol, such as cold and flu remedies. An overdose can cause serious liver damage, sometimes without early symptoms, so seek help straight away."),
        ],
        [
            ("h2", "3. Ibuprofen and other NSAIDs"),
            ("p", "Take with food. Avoid in people with a history of stomach ulcer or bleeding, kidney disease, heart failure, or aspirin-sensitive asthma. Use the lowest dose for the shortest time."),
            ("h2", "4. Allergy to medicines"),
            ("p", "Penicillin allergy can cause a rash, swelling or trouble breathing. Record the medicine and the reaction in the notes and tell every prescriber. Seek emergency help for swelling of the face or throat or difficulty breathing."),
        ],
        [
            ("h2", "5. Medicine list and interactions"),
            ("p", "Keep an up-to-date list of all medicines, including herbal products, and show it to every pharmacist and doctor. Check for interactions before starting a new medicine. Warfarin, for example, interacts with many antibiotics and with aspirin."),
            ("h2", "6. Children and storage"),
            ("p", "Store medicines out of reach and sight of children, in the original container. Use the measuring device supplied with liquid medicines and never a kitchen spoon. Take unused medicines back to a pharmacy."),
        ],
    ],
}


def build(name, spec):
    total = len(spec["pages"])

    def furniture(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(20 * mm, A4[1] - 12 * mm, NOTE)
        canvas.drawString(20 * mm, 10 * mm, spec["short"])
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {doc.page} of {total}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUT / name), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm, bottomMargin=20 * mm,
        title=spec["title"], author="Example Clinical Guidelines Group", subject=spec["subject"],
    )
    doc.creator = "Example Guideline Writer"
    story = [Paragraph(spec["title"].replace(" (Example)", ""), H1)]
    for number, page in enumerate(spec["pages"]):
        if number:
            story.append(PageBreak())
        for kind, value in page:
            if kind == "h2":
                story.append(Paragraph(value, H2))
            elif kind == "h3":
                story.append(Paragraph(value, H3))
            elif kind == "p":
                story.append(Paragraph(value, BODY))
            elif kind == "bullets":
                for item in value:
                    story.append(Paragraph(item, ITEM, bulletText="-"))
                story.append(Spacer(1, 4))
            elif kind == "table":
                rows = [[Paragraph(c, CELL_HEAD if r == 0 else CELL) for c in row] for r, row in enumerate(value)]
                width = A4[0] - 40 * mm
                cols = len(value[0])
                table = Table(rows, colWidths=[width / cols] * cols if cols != 3 else [width * 0.38, width * 0.27, width * 0.35])
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#333333")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0fa")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
                story.append(Spacer(1, 8))
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)


def main():
    OUT.mkdir(exist_ok=True)
    for name, spec in GUIDES.items():
        build(name, spec)
        print("wrote", name)


if __name__ == "__main__":
    main()
