# IndiaPix Metadata Automation System — User Manual

*For Sneha, Anushka, and the IndiaPix Metadata Team*

---

## Overview

The IndiaPix Metadata Automation System generates professional stock metadata for your video files using AI (Claude by Anthropic or GPT-4o by OpenAI). It replaces the manual keywording process, reducing turnaround time from 10–20 minutes per file to approximately **2–3 minutes**.

The system:
1. Takes a video file (MP4, MOV, AVI, MXF, etc.) — images can also be uploaded
2. Automatically extracts key frames based on video length
3. Sends frames to the selected AI provider (Claude or GPT-4o) for analysis
4. Returns ready-to-export metadata — title, caption, description, and 50 keywords across 6 categories
5. Lets you review and edit before exporting as CSV

---

## Getting Started

### Opening the Application

1. Make sure the application is running (ask your IT team if not)
2. Open **Google Chrome** (recommended) or any modern browser
3. Go to: **http://localhost:3000**

You should see the IndiaPix Metadata Automation System home page.

---

## Step-by-Step Workflow

### Step 1: Upload a File

1. On the home page, you'll see a **large dashed box** — this is the upload area
2. **Drag & drop** a video or image file onto the box, OR **click** the box to browse and select a file
3. Supported formats:
   - **Videos:** MP4, MOV, AVI, MXF, M4V, WMV
   - **Images:** JPG, JPEG, PNG, TIFF, TIF

After uploading, you'll see:
- The file name and size
- **For videos:** Duration (e.g., "1m 34s"), frame count, resolution, frame rate, aspect ratio, bitrate, audio info, and date created badges
- **For images:** File name and size only
- An **"Uploaded"** badge in green

> **Note:** Image upload is supported for storage/validation only. Metadata generation currently works with video files only. If you upload an image and attempt to generate metadata, you will see an error message.

### Step 2: Add Context (Optional)

Below the file info, you'll find a **Description** text box. This is optional but helpful for the AI.

**Good examples:**
- "Wedding ceremony in Jaipur, shot at sunset"
- "Street food vendor in Old Delhi market"
- "School children in rural Rajasthan village"

The AI uses this context to generate more accurate metadata.

### Step 3: Select AI Model

Before generating metadata, you can choose which AI provider to use:

- **Claude (Anthropic)** — Default provider
- **GPT-4o (OpenAI)** — Alternative provider

Click the toggle button to switch between providers. A provider will be greyed out and disabled if its API key is not configured (check with your IT team).

### Step 4: Generate Metadata

Click the **"Generate Metadata"** button.

The system will now:
1. Extract frames from your video at strategic points
2. Send the frames to the selected AI provider along with the description
3. Wait for the AI to analyze and generate metadata

**Estimated wait time: 10–30 seconds.**

While waiting, you'll see a spinning animation with the message "Generating Metadata..." and a **Cancel Generation** button if you need to stop.

> **Image files:** Metadata generation is not yet supported for images. If you upload an image, the Generate button will still appear, but the backend will return an error. This limitation will be addressed in a future update.

### Step 5: Review & Edit Metadata

Once complete, the metadata will appear in editable fields:

| Field | Description | Character Limit |
|---|---|---|
| **Title** | Main headline for the stock platform | 200 characters |
| **Description** | 2-3 sentence detailed description | — |
| **Category** | Primary stock category (e.g., Education, Travel) | — |
| **Location** | Detected location (City, State, India) | — |
| **Mood** | Atmospheric description (3–5 words) | — |
| **Shot Type** | Wide, medium, close, aerial, etc. | — |
| **Editorial** | Yes = Editorial use / No = Commercial use | — |

**Editing tips:**
- **Title**: Make sure it follows "Subject + Action + Location" format. Character counter turns red when close to 200.
- **Description**: First sentence = who + what, Second = where + setting, Third = mood + cultural context.

### Step 6: Review Keywords

Keywords are displayed in **6 categories** below the main metadata:

| Category | Count | Description |
|---|---|---|
| People & Demographics | 5–8 | Indian woman, school students, farmer |
| Action & Activity | 5–8 | conducting experiment, harvesting |
| Location & Geography | 5–8 | India, New Delhi, Rajasthan |
| Setting & Environment | 5–7 | laboratory, field, market |
| Technical & Shot Type | 3–5 | wide shot, close up, natural light |
| Conceptual & Thematic | 8–12 | education, STEM, culture |

You can **remove individual keywords** by clicking the **× (cross)** button next to any keyword.

### Step 7: Export as CSV

When you're satisfied with the metadata:

1. Click **"Export CSV"**
2. The file will download automatically
3. The CSV file is named: `[original filename]_metadata.csv`

The CSV format matches **Getty Images** and **Adobe Stock** bulk upload specifications. Columns include: filename, title, description, keywords, category, editorial, location, shot_type, mood.

### Step 8: Process the Next File

Click **"Process Next File"** to clear the current result and upload a new file.

---

## Tips for Best Results

| Do | Don't |
|---|---|
| Add a brief description context before generating | Leave the description field empty if you have useful context |
| Review and edit the title (max 200 chars) | Upload files without checking the output |
| Ensure keywords cover all 6 categories | Export without reviewing |
| Check editorial flag — when in doubt, mark as Editorial | Use trademarked brand names as keywords |
| Use India/Indian in location keywords | Repeat the same keyword |

---

## Understanding the Editorial Flag

The system automatically determines if content is **Editorial** or **Commercial**:

**Flag as Editorial if the content has:**
- Visible brand logos or signboards
- Identifiable people without model releases
- Government buildings with signage
- News events or religious ceremonies
- Trademarks or copyrighted material

**Commercial** (default): Generic scenes, landscapes, abstract content, studio shoots.

**Rule of thumb:** When in doubt — flag as Editorial. It's safer.

---

## Troubleshooting

| Problem | What to Do |
|---|---|
| **Upload doesn't work** | Check file format (video: MP4, MOV, AVI, MXF, M4V, WMV / image: JPG, PNG, TIFF) and size (under 2GB) |
| **Image upload gives error on Generate** | Metadata generation is currently only supported for video files. Use a video file instead. |
| **Generation takes too long** | Wait up to 60 seconds. Longer videos take more time for frame extraction |
| **Error message appears** | Note the error text and contact your IT team with a screenshot |
| **CSV won't download** | Check browser pop-up blocker settings |
| **Wrong location detected** | Edit the location field manually before export |
| **Too few/many keywords** | You can remove keywords in the keyword section |
| **AI Provider not available** | Check with your IT team that the API key for your chosen provider is configured in the backend |

---

## Support

For help or questions:

- **Hemant Mehta** — hemant@indiapicture.in
- **Anushka** — Day-to-day coordination and testing
- **Sneha** — End user testing and feedback

---

*IndiaPix Visual Media Pvt. Ltd. | New Delhi, India | Est. 1993*
*Powered by Claude AI (Anthropic) & GPT-4o (OpenAI)*