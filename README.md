# Workforce Intelligence — AI-Powered HR Analytics

An enterprise web application for employee attrition prediction, workforce planning, and talent intelligence, built with Python (Flask), Scikit-Learn, XGBoost, and vanilla JavaScript with Chart.js.

> [!NOTE]
> **Synthetic Dataset Notice:** Demonstration application using synthetic workforce data. Predictions and planning estimates are illustrative decision-support outputs and must not be treated as actual employee outcomes or used for automated adverse employment actions.

---

## 1. Project Overview & Features

Workforce Intelligence delivers five integrated dashboards matching high-fidelity enterprise reference designs:

1. **Dashboard Overview (`/`)**: Executive workforce summary with 6 primary KPIs (Headcount, Historical Attrition, Serving Notice, Predicted High Risk, Open Requisitions, Staffing Gap), Department Headcount, Attrition Outcome Distribution, Department Attrition Rates, Predicted Risk Distribution, Notice Exits by Month, Target vs Current Headcount, Recruitment Funnel, Recruitment Cost Breakdown in INR, and dynamic insights.
2. **Employee & Department Analytics (`/analytics`)**: Departmental workforce trends, tenure distribution, job satisfaction, overtime hours, training hours, interactive multi-attribute filter bar (Department, Job Role, Job Level, Location, Employment Type, Tenure range slider), searchable and sortable Employee Details table with server-side pagination, and side-by-side Department Comparison.
3. **AI Attrition Prediction (`/prediction`)**: 6-month attrition risk probability scored by trained Machine Learning models across all 47,972 eligible non-notice employees. Filterable risk prediction table with instant employee inspection panel showing top contributing factors (relative to population baselines) and practical, supportive retention action checklists.
4. **Workforce Planning & Exit Analysis (`/workforce`)**: Separation of confirmed notice-period exits (2,028 records) from model-predicted additional exits. Department exit analysis table, monthly exit allocation, open requisitions by department, notice period days remaining distribution, paginated notice employees list, and an interactive **Workforce Scenario Planner** computing dynamic staffing gaps in real time.
5. **Model Performance & Data Quality (`/model-quality`)**: Comparison of 5 machine learning classification algorithms (Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost) on held-out test data (80/20 stratified split). Displays Accuracy, Precision, Recall, F1-Score, ROC-AUC, and PR-AUC, Confusion Matrix, interactive ROC Curve, Precision-Recall Curve, global Feature Importance, Risk Score Probability Distribution, 10 automated Data Quality Audits, Dataset Summary, and a one-click **Retrain Model** workflow.
6. **Workforce Segmentation & Talent Intelligence (`/segmentation`)**: Unsupervised clustering (K-Means with configurable K) segmenting the 47,972 active non-notice employees across 11 standardized workplace features and 3 categorical dimensions. Derives `Compa_Ratio` relative to Job Level medians, excludes simulated labels and sensitive demographics during training, and performs post-hoc attrition validation and demographic fairness auditing. Includes job role staffing pressure clustering across all 26 roles, Isolation Forest workload/pay anomaly detection (960 flagged profiles), and real-time interactive reclustering.

---

## 2. Technology Stack

- **Backend & ML:** Python 3.11+, Flask 3.1+, Pandas, openpyxl, NumPy, Scikit-Learn, XGBoost, Joblib.
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+), Chart.js 4.4+, Bootstrap Icons.
- **Data Layer:** Excel-first in-memory cached architecture (`openpyxl` / `pandas`). Zero external SQL database dependencies.
- **Deployment:** WSGI-ready (`gunicorn app:application`), configurable host/port, environment variable support.

---

## 3. Project Directory Structure

```text
workforce-intelligence/
├── app.py                      # Flask Application factory & WSGI entry point
├── config.py                   # Configuration, thresholds, and auto path discovery
├── requirements.txt            # Python dependencies
├── Procfile                    # Production WSGI process definition
├── .env.example                # Sample environment configuration
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete documentation and run instructions
│
├── segment_workforce.py        # Unsupervised workforce segmentation reference script
│
├── src/                        # Core algorithmic modules
│   ├── __init__.py
│   └── segmentation.py         # Configurable K-Means, role pressure, and anomaly detection
│
├── data/                       # Excel dataset location
│   ├── Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx
│   └── Employee_Attrition_Workforce_Planning_Expert_Dataset_Corrected.xlsx
│
├── models/                     # Persisted model pipelines and evaluation cache
│   ├── trained_models.joblib
│   ├── preprocessor.joblib
│   ├── segmentation_pipeline.joblib
│   └── evaluation_results.json
│
├── artifacts/ / outputs/       # Generated reports, segment profiles, and analysis logs
│   ├── segment_profiles.json
│   ├── role_staffing_pressure.csv
│   ├── workload_pay_anomalies.csv
│   └── k_evaluation_metrics.json
│
├── services/                   # Modular service architecture
│   ├── __init__.py
│   ├── excel_service.py              # In-memory cached workbook loader & name mapper
│   ├── data_validation_service.py    # 10 data quality and referential integrity checks
│   ├── preprocessing_service.py      # Feature engineering, scaling, one-hot encoding
│   ├── model_training_service.py     # 5-algorithm trainer, evaluator, and persister
│   ├── prediction_service.py         # Cohort inference, risk categorizer, factor explainer
│   ├── analytics_service.py          # Departmental aggregations and comparison
│   ├── workforce_planning_service.py # Notice period tracking and scenario levers
│   ├── recruitment_service.py        # Candidate funnel and recruitment costs in INR
│   └── segmentation_service.py       # Unsupervised segmentation caching & dynamic reclustering
│
├── routes/                     # Clean Flask Blueprint route definitions
│   ├── __init__.py
│   ├── dashboard_routes.py     # Overview page and /api/dashboard/*
│   ├── analytics_routes.py     # Analytics page and /api/analytics/*
│   ├── prediction_routes.py    # Prediction page and /api/prediction/*
│   ├── workforce_routes.py     # Workforce page and /api/workforce/*
│   ├── model_quality_routes.py # Model quality page and /api/model-quality/*
│   └── segmentation_routes.py  # Segmentation page and /api/segmentation/*
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Shared layout, enterprise sidebar, header, synthetic banner
│   ├── dashboard.html          # Page 1: Dashboard Overview
│   ├── analytics.html          # Page 2: Employee & Department Analytics
│   ├── prediction.html         # Page 3: AI Attrition Prediction
│   ├── workforce.html          # Page 4: Workforce Planning & Exit Analysis
│   ├── model_quality.html      # Page 5: Model Performance & Data Quality
│   ├── segmentation.html       # Page 6: Workforce Segmentation & Talent Intelligence
│   ├── 404.html                # Custom 404 error page
│   └── 500.html                # Custom 500 error page
│
├── static/                     # Static assets
│   ├── css/
│   │   ├── style.css           # Core design system tokens, typography, grid, segmentation UI
│   │   └── responsive.css      # Responsive media queries (desktop/tablet/mobile)
│   └── js/
│       ├── api.js              # Reusable fetch API client
│       ├── common.js           # Chart.js helper, modal controller, formatters
│       ├── dashboard.js        # Page 1 controller
│       ├── analytics.js        # Page 2 controller
│       ├── prediction.js       # Page 3 controller
│       ├── workforce.js        # Page 4 controller
│       ├── model_quality.js    # Page 5 controller
│       └── segmentation.js     # Page 6 controller
│
└── tests/                      # Automated test suite
    ├── test_data_loading.py
    ├── test_data_validation.py
    ├── test_analytics.py
    ├── test_model_training.py
    ├── test_api_routes.py
    ├── test_workforce_planning.py
    └── test_segmentation.py
```

---

## 4. Local Execution Instructions (Windows)

### Step 1: Set up a Python Virtual Environment
```powershell
py -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install Required Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run Workforce Segmentation Standalone
```powershell
python segment_workforce.py --k 5
```

### Step 4: Run the Application
```powershell
python app.py
```

Open your browser and navigate to:
**`http://127.0.0.1:5000`** (or **`http://127.0.0.1:5000/segmentation`**)

---

## 5. Running Automated Tests

Run the complete test suite containing **35 test cases** across data loading, schema validation, analytics, ML evaluation, API routes, workforce planning, and unsupervised segmentation:

```powershell
python -m unittest discover tests
```

---

## 6. Model Training & Retraining

On the first application start, the application fits the preprocessor and all 5 classification models on the 47,972 eligible non-notice employee records using an 80/20 stratified split (`random_state=42`) and saves the fitted pipelines and metrics to `models/`.

Subsequent starts load the persisted artifacts instantly.

To retrain the models:
- Click the **Retrain Model** button at the top right of the **Model Performance & Data Quality** page (`/model-quality`).
- Or send a `POST` request to `/api/model-quality/retrain`.
- The system retrains all 5 algorithms, updates held-out evaluation metrics, recomputes confusion matrices, curves, feature importances, and updates the active prediction cache in memory.

---

## 7. Production Deployment (WSGI & Linux)

The application is WSGI-compliant and ready for hosting on Python platforms (e.g. Render, Railway, AWS EC2, Heroku, Azure):

1. Set environment variables:
   - `PORT=8000` (or platform default)
   - `FLASK_DEBUG=False`
   - `SECRET_KEY=your-production-secret-key`
   - `DATASET_PATH=data/Employee_Attrition_Workforce_Planning_Expert_Dataset.xlsx`
2. Ensure the Excel dataset file is committed or copied to the deployment server's `data/` directory.
3. Start the production WSGI server using Gunicorn:
   ```bash
   gunicorn app:application --workers 2 --timeout 120 --bind 0.0.0.0:$PORT
   ```
