"""Generate the two small demo PDFs in sample_docs/ (fictional company, self-written text).

Run from backend/:  python scripts/make_sample_docs.py     (needs reportlab: requirements-dev.txt)
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parents[1] / "sample_docs"

HANDBOOK = [
    ("1. Working hours and attendance", [
        "1.1 Standard week. The standard working week is 40 hours, Monday to Friday. Employees may start work at any time between 8:00 and 10:00 and finish eight hours later.",
        "1.2 Core hours. All employees must be available during core hours, 10:00 to 16:00 local time, for meetings and team collaboration.",
        "1.3 Remote work. Employees may work remotely up to 3 days per week with the approval of their manager. Fully remote arrangements need written approval from the department head.",
        "1.4 Probation. New employees complete a probation period of 3 months. A probation review meeting takes place in the final two weeks of that period.",
    ]),
    ("2. Leave policy", [
        "2.1 Annual leave. Full-time employees receive 24 days of paid annual leave per year. Part-time employees receive annual leave in proportion to their working hours.",
        "2.2 Carry forward. Employees may carry forward up to 5 unused annual leave days into the next year. Carried-forward days must be used by March 31, or they expire.",
        "2.3 Sick leave. Employees receive 10 paid sick days per year. A medical certificate is required after 3 consecutive days of sick leave.",
        "2.4 Parental leave. The primary caregiver receives 16 weeks of paid parental leave. The secondary caregiver receives 4 weeks of paid parental leave.",
        "2.5 Bereavement leave. Employees receive 5 days of paid leave on the death of an immediate family member and 2 days for an extended family member.",
    ]),
    ("3. Travel and expenses", [
        "3.1 Submission deadline. Expense claims must be submitted within 30 days of the date the expense was incurred. Late claims may be rejected by the finance team.",
        "3.2 Receipts and approval. A receipt is required for every expense above $25. Purchases above $500 also need approval from the employee's manager before they are made.",
        "3.3 Meals. While travelling on company business, employees may claim a meal allowance of up to $60 per day.",
        "3.4 Flights and hotels. Employees must book economy class for flights shorter than 6 hours. Hotel stays are reimbursed up to $180 per night.",
    ]),
    ("4. Performance and development", [
        "4.1 Reviews. Performance reviews take place twice a year, in June and in December. Each review includes a goal-setting conversation with the manager.",
        "4.2 Learning budget. Every employee has a learning budget of $1,200 per year for courses, books, and conferences related to their role.",
        "4.3 Promotions. Promotion decisions are made once a year, in January, after the December review has been completed.",
        "4.4 Notice period. After probation, the notice period for resignation is 60 days. During probation the notice period is 14 days.",
    ]),
]

IT_POLICY = [
    ("1. Accounts and passwords", [
        "1.1 Password length. Passwords must be at least 14 characters long and must not reuse any of the previous 10 passwords.",
        "1.2 Password rotation. Passwords must be changed every 180 days, or immediately if a compromise is suspected.",
        "1.3 Multi-factor authentication. Multi-factor authentication is required for all company accounts, including email and the VPN.",
        "1.4 Screen lock. Computers must lock automatically after 5 minutes of inactivity.",
    ]),
    ("2. Devices and data", [
        "2.1 Laptops. All company laptops use full disk encryption. Lost or stolen devices must be reported to the security team at once.",
        "2.2 Personal devices. Personal phones and laptops may access company email only after enrolment in the mobile device management (MDM) system.",
        "2.3 USB storage. USB storage devices are disabled by default. Requests to enable USB storage must be approved by the security team.",
        "2.4 Data classes. Company data is classified as Public, Internal, Confidential, or Restricted. Confidential data must never be sent through personal email accounts.",
    ]),
    ("3. Incident response", [
        "3.1 Phishing reports. Suspected phishing emails must be reported to security@northwind.example within 1 hour of discovery.",
        "3.2 Acknowledgement. The security team acknowledges every report within 2 hours.",
        "3.3 Severity levels. Incidents are rated P1 (critical), P2 (high), or P3 (low). For a P1 incident the security team responds within 15 minutes.",
        "3.4 Backups. Company systems are backed up daily, and backups are kept for 30 days.",
        "3.5 Training. All employees complete security awareness training once a year.",
    ]),
]


def build(filename: str, title: str, sections: list) -> None:
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Heading2"], spaceAfter=10)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=11, leading=15, spaceAfter=8)
    doc = SimpleDocTemplate(str(OUT / filename), pagesize=A4, title=title, author="Northwind (sample)",
                            leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2.2 * cm, bottomMargin=2.2 * cm)
    story = []
    for i, (heading, clauses) in enumerate(sections):
        if i:
            story.append(PageBreak())
        if i == 0:
            story += [Paragraph(title, styles["Title"]), Spacer(1, 6)]
        story.append(Paragraph(heading, h))
        story += [Paragraph(c, body) for c in clauses]
    doc.build(story)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build("northwind_employee_handbook.pdf", "Northwind Employee Handbook", HANDBOOK)
    build("northwind_it_security_policy.pdf", "Northwind IT Security Policy", IT_POLICY)
    print("Wrote sample PDFs to", OUT)
