# ⚖️ MetroTest-76 (SIH26035)

> **Next-Generation Computer Vision & Legal Metrology Inspection Platform**  
> *Developed for Smart India Hackathon 2026 | Ministry of Consumer Affairs, Food & Public Distribution*  
> **Team:** DEVVVS

---

## 🌟 Key Capabilities
- **Dual-Modal Vision Extraction:** Automated extraction from stamped industrial nameplates (EasyOCR/CRAFT) and 7-segment digital weight displays (LED/LCD).
- **Automated OIML R-76 MPE Engine:** Real-time stepped tolerance checking ($\pm0.5e, \pm1.0e, \pm1.5e$) across Linearity, Eccentricity (1/3 Max), Repeatability, and Tare tests.
- **Section 63 BSA 2023 Court Admissibility:** Cryptographic SHA-256 evidence bundle with geotagging and real-time timestamping.
- **1-Second Statutory Re-Audit QR System:** Scanning previous certificate QR instantly loads machine specifications and launches verification testing directly.
- **Pre-Packaged Commodities (PCR 2011) Verification:** Automated compliance check for Rule 6 mandatory declarations and Unit Sale Price (USP).
- **Dual Role Access Control:** Segregated Inspector field mode and Zonal Supervisor administrative registry.

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone the repository
git clone <repo-url>
cd metrotest76

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the application
python run_metrotest.py
```
Open **`http://localhost:8007`** in your browser.

---

## ☁️ Deployment

### Deploy on Render / Railway
1. Push this repository to GitHub.
2. Link the repository on [Render](https://render.com) or [Railway](https://railway.app).
3. The included `Procfile` and `Dockerfile` configure the web server automatically.

### Deploy with Docker
```bash
docker build -t metrotest76 .
docker run -p 8007:8007 metrotest76
```

---

## 🏛️ Statutory Compliance
- **OIML R 76-1:2006 & R 76-2:2007:** Non-Automatic Weighing Instruments
- **Bharatiya Sakshya Adhiniyam (BSA), 2023:** Section 63 Electronic Evidence Certificate
- **The Legal Metrology Act, 2009 & General Rules, 2011**
- **The Legal Metrology (Packaged Commodities) Rules, 2011**
