FINHER PROJECT 

FinHer is a prototype Fintech platform designed to score the creditworthiness of women entrepreneurs in East Africa leveraging alternative data sources as opposed to traditional collateral, pay slips and bank credit history that exclude the majority of women in the informal sector.

A prototype of a Software Engineering course designed to demonstrate the main functional requirements outlined in the FinHer SRS document.

Live Demo

Live URL: https://finher-prototype.onrender.com


Please note: This app is on Render's free tier, which shuts down when inactivity occurs. The initial visit may take 30s to 60s depending on how long it takes for the server to wake up, before this page loads do not refresh. 

Demo accounts: 
Role:Lender admin   User_name :Mutoni_lender   Password:Demo@2026 
Role:System Admin   User_name :Mutoni_admin   Password:Demo@2026 
You can also register as a new Borrower directly on the site via "I’m a Woman Entrepreneur" on the landing page. No specific credentials needed.

What This Prototype Includes
Landing page — mission, problem statement, and proposed solution
Borrower flow — self-registration, entering financial activity data, and viewing a real-time generated FinHer Score with plain-language explanation
Lender Admin dashboard — list of applicants, scores, and credit decisions (Approve / Reject / Defer)
System Admin dashboard — user management, model info, audit log, and a fairness monitoring view comparing average scores across locations
Trained ML scoring engine — a logistic regression model (scikit-learn) trained on synthetic data, used to generate real-time scores
REST API endpoint — GET /api/score/<entrepreneur_id> returns a JSON score breakdown for a given applicant
PostgreSQL database — relational schema covering entrepreneurs, mobile money transactions, SACCO memberships, informal trade records, credit scores, credit decisions, loan applications, and users.
Tech Stack
Backend: Python, Flask
Database: PostgreSQL
ML: scikit-learn (logistic regression), joblib for model persistence
Frontend: HTML/CSS (Jinja2 templates), Font Awesome icons
Deployment: Render (web service + managed PostgreSQL)
Roles & Access
For the SRS's actor design, there are 3 User-Roles of FinHer.
Borrower (Woman Entrepreneur): registers herself, enters her own financial activity and views her own score. For this flow no login is required.
Admin: Normal sign up. Approves, disapproves or defers applicants and determines credit.
System Admin: Internal, not self-service (Sign up for security reasons). Manages users, monitors model health, audits and monitors fairness dashboard. Unlike a real financial institution, it's not possible for System Admins to make credit decisions.
Local Setup Instructions
Read the instructions below to run FinHer on your own machine.
1. Clone the repository
git clonehttps://github.com/keira9/FinHer_prototype.git
cd FinHer_prototype
2. Install Python dependencies
Requires Python 3.10+.
pip install -r requirements.txt
3. Set up PostgreSQL
Set up PostgreSQL (or pgAdmin) and set up a database, e.g. FinHer.
Use the schema and seed data scripts in database/schema.sql (or see the CREATE TABLE statements in this repo's commit history) to set up:
entrepreneur
mobilemoneytransaction
saccomembership
informaltraderecord
creditscore
users
creditdecision
loanapplication
4. Configure database connection
Open app.py and change the local fallback credentials in get_connection() to match your own set up with PostgreSQL:
return psycopg2.connect(
    dbname="FinHer",
    user="postgres",
    password="your_password",
    host="localhost"
    port="5432"
)
Or, you can configure an environment variable DATABASE_URL and the app will use this one by default instead.
5. Train the ML model (first time only)
python train_model.py
This will create a finher_model.pki and finher_scaler.pki that will be loaded during runtime.
6. Run the app
  python app.py
Visit  http://127.0.0.1:5000 in your browser.


Project Structure
FinHer_prototype/
├── app.py                  # Main Flask application and routes
├── train_model.py          # Trains the logistic regression scoring model
├── finher_model.pkl        # Trained model (generated)
├── finher_scaler.pkl       # Feature scaler (generated)
├── requirements.txt
├── Procfile                 # Render deployment start command
├── templates/
│   ├── landing.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── detail.html
│   ├── admin.html
│   ├── fairness.html
│   ├── check_score.html
│   ├── register_borrower.html
│   ├── add_activity.html
│   └── base.html
└── README.md


Known Limitations (Honest Scope Notes)
This is a course prototype and is not a production system. Notable simplifications:
No Live Integration with Real Mobile Money interfaces (Safaricom Daraja, MTN MoMo, Airtel Money) — Fall Back Mechanism is explicitly stated in the SRS (Section 2.7) as Self Reported data entry in case of no Live API access.
The ML model is trained with artificial data, rather than the real history of applicants.
Fairness monitoring involves comparing averages by location as a simple proxy of the formal metric of fairness in the SRS (e.g. statistical parity) — a production system would enable this to be extended.
No real partnerships between regulators and lenders/MFIs and no integration of the regulatory sandboxes. 
Author: MUTONI KEIRA , Software Engineering , African Leadership University.
