# Sample Flood Images for ScoutAgent

This directory contains sample flood images for simulation mode.

## Directory Structure

```
sample_images/
├── flood_levels/
│   ├── ankle_deep_*.jpg     # 0.1-0.15m flood depth
│   ├── knee_deep_*.jpg      # 0.3-0.45m flood depth
│   ├── waist_deep_*.jpg     # 0.6-0.9m flood depth
│   └── chest_deep_*.jpg     # 1.0-1.5m flood depth
└── README.md
```

## Adding Real Images

To add real flood images for testing:

1. Source images from:
   - Wikimedia Commons (search "flooding Philippines")
   - Public domain news archives
   - PAGASA/NDRRMC public reports
   - Your own photos (with permission)

2. Name images according to flood depth:
   - `ankle_deep_01.jpg` - Minor flooding (~0.15m)
   - `knee_deep_01.jpg` - Moderate flooding (~0.4m)
   - `waist_deep_01.jpg` - Severe flooding (~0.8m)
   - `chest_deep_01.jpg` - Critical flooding (~1.2m)

3. Recommended image specs:
   - Format: JPEG or PNG
   - Size: 640x480 to 1920x1080
   - Clear visibility of water level indicators (vehicles, people, landmarks)

## Simulated Mode

When real images are not available, the system uses `SimulatedImageAnalyzer`
which returns pre-defined analysis based on the filename pattern.

This allows testing the full pipeline without requiring:
- Actual flood images
- Running Ollama/Qwen 3-VL
- GPU resources

## Example Usage

```python
# In synthetic tweet data:
{
    "tweet_id": "123",
    "text": "Baha sa J.P. Rizal!",
    "image_path": "app/data/sample_images/flood_levels/knee_deep_01.jpg",
    ...
}
```
