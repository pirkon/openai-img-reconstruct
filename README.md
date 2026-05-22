# openai-img-reconstruct

Batch-replaces the subject in any photo with a custom character reference, using **Claude** for scene analysis and **gpt-image-2** for generation.

## How it works

For each image in `/input`:

1. **Claude (claude-sonnet-4-6)** analyzes the photo and writes a highly detailed generation prompt — covering the scene, lighting, outfit, pose, background, and photographic style — without referencing the original subject's identity.
2. **gpt-image-2** receives that prompt plus your character reference image from `/character` and generates a new photo: same scene, same clothes, same vibe — but with your character as the subject.

## Prerequisites

- Python 3.9+
- An **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com)
- An **OpenAI API key** — [platform.openai.com](https://platform.openai.com)

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/openai-img-reconstruct.git
cd openai-img-reconstruct

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

## Configuration

Open `.env` and fill in your API keys:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
```

## Folder structure

```
openai-img-reconstruct/
├── input/          ← Place source photos here (jpg, jpeg, png, webp)
├── character/      ← Place ONE character reference photo here
├── output/         ← Generated images appear here (created automatically)
├── charoverlay.py
├── requirements.txt
└── .env            ← Not committed — add your own keys
```

## Usage

```bash
python charoverlay.py
```

The script processes every image in `/input` and saves outputs to `/output` as `<original_name>_output.png`.

### Options

| Flag | Default | Description |
|---|---|---|
| `--size` | `1024x1024` | Output dimensions: `1024x1024`, `1536x1024`, `1024x1536` |
| `--quality` | `high` | Output quality: `low`, `medium`, `high`, `auto` |
| `--save-prompts` | off | Also save each Claude-generated prompt as a `.txt` file in `/output` |

### Examples

```bash
# Standard run
python charoverlay.py

# Portrait outputs, save prompts for review
python charoverlay.py --size 1024x1536 --save-prompts

# Fast low-cost test run
python charoverlay.py --quality low
```

## Tips

- Use a clean, well-lit, front-facing portrait for your character reference — it gives gpt-image-2 the clearest identity signal.
- Input images with a clear, identifiable subject and a distinct setting produce the best results.
- Use `--save-prompts` to inspect what Claude generates — useful for debugging or tuning.
- Each image costs one Claude vision call + one gpt-image-2 generation. Use `--quality low` for bulk testing.

## Cost estimate

| Step | Model | ~Cost per image |
|---|---|---|
| Scene analysis | claude-sonnet-4-6 | ~$0.003 |
| Image generation | gpt-image-2 (high) | ~$0.19 |
| **Total per image** | | **~$0.19** |

*Costs vary with input image size and output quality setting.*
