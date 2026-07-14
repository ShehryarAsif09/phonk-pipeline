# Phonk Pipeline: Manual Setup & Configuration Steps

Complete the following steps once to enable automated zero-cost ($0) daily phonk track generation across private GitHub Actions workflows and Kaggle GPU kernels.

---

## 1. Kaggle Account & API Token Setup
1. Create a free Kaggle account at [kaggle.com](https://www.kaggle.com/).
2. Navigate to **Settings** (`https://www.kaggle.com/settings`).
3. Under **API**, click **Create New Token**. This downloads a `kaggle.json` file containing your `username` and `key`.

---

## 2. GitHub Actions Secrets Setup
1. In your GitHub repository (`phonk-pipeline`), go to **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret** and add:
   - `KAGGLE_USERNAME`: Your exact Kaggle username from `kaggle.json`.
   - `KAGGLE_KEY`: Your exact API key from `kaggle.json`.

> **Note on Private Repository Minutes:** Because this pipeline is split into `trigger-generation.yml` (Workflow A) and `package-and-publish.yml` (Workflow B) rather than long-polling inside a single job, each daily run consumes approximately 2 to 3 minutes of runner compute. This ensures execution comfortably stays well below GitHub's `2000 minutes/month` free tier limit for private repositories.

---

## 3. Persistent Checkpoint Caching (Phase 4 Setup)
To prevent Kaggle from burning GPU quota downloading model weights on every scheduled run:
1. Open a temporary Kaggle Notebook session or download locally:
   - `acestep-v15-turbo` DiT weights
   - `acestep-5Hz-lm-0.6B` Language Model weights
2. Go to **Kaggle -> Datasets** and click **New Dataset**. Upload the downloaded weights as a **Private Dataset** named `acestep-v15-checkpoints`.
3. Update `dataset_sources` inside `kaggle/kernel-metadata.json` with your dataset identifier (`YOUR_KAGGLE_USERNAME/acestep-v15-checkpoints`).
4. At runtime, `kaggle_kernel.py` automatically detects `/kaggle/input/...` and symlinks weights directly into `ACE-Step-1.5/checkpoints/` with zero network download overhead.

---

## 4. Phase 6 Manual End-to-End Test
Before relying on the daily cron:
1. Run a small manual test batch (`count = 2`) inside a Kaggle notebook session using `kaggle/kaggle_kernel.py`.
2. Verify that `api.kernels_status("YOUR_KAGGLE_USERNAME/phonk-batch-generator")` returns the expected shape (Workflow B logs raw object representation for exact verification).
3. Confirm audible `.wav` files and valid release packaging.
