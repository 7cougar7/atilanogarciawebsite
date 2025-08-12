# FontAwesome Static Files Setup

This document explains how FontAwesome static files are managed in this Django project.

## Overview

Instead of installing FontAwesome via npm or CDN, we keep the full FontAwesome zip file in the repository and extract it to the correct static directory during the build process. This ensures:

- All FontAwesome icons are available (not just a subset)
- No external dependencies during build
- Consistent FontAwesome version across deployments
- Offline capability

## Files

- `mainwebsite/static/fontawesome-free-6.7.2.zip` - The complete FontAwesome package (committed to repo)
- `mainwebsite/static/fontawesome/` - Extracted FontAwesome files (not committed, generated during build)
- `scripts/setup_fontawesome.py` - Python script that extracts FontAwesome to static directory
- `scripts/build.sh` - Build script that runs FontAwesome setup before collectstatic

## How It Works

1. **Storage**: The complete FontAwesome zip file is stored in `mainwebsite/static/fontawesome-free-6.7.2.zip`
2. **Git Tracking**: Only the zip file is committed; extracted files are ignored via `.gitignore`
3. **Extraction**: The `scripts/setup_fontawesome.py` script extracts the zip to `mainwebsite/static/fontawesome/`
4. **Build Integration**: The build script runs FontAwesome setup before Django's collectstatic
5. **Static Collection**: Django's collectstatic copies all FontAwesome files to the final static directory

## Repository Structure

```
atilanogarciawebsite/
├── mainwebsite/
│   └── static/
│       ├── fontawesome-free-6.7.2.zip     # Committed to repo
│       └── fontawesome/                    # Generated during build (not committed)
│           ├── css/
│           ├── webfonts/
│           ├── js/
│           └── ...
├── scripts/
│   ├── setup_fontawesome.py               # Extraction script
│   └── build.sh                          # Build script
└── .gitignore                            # Excludes extracted files
```

## Build Process

The build process follows this sequence:

```bash
# 1. Activate virtual environment (if exists)
source venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Extract FontAwesome to static directory
python scripts/setup_fontawesome.py

# 4. Run Django migrations
python manage.py migrate

# 5. Collect all static files
python manage.py collectstatic --noinput --clear
```

## Manual Setup

If you need to manually set up FontAwesome:

```bash
python scripts/setup_fontawesome.py
```

This will:
- Remove any existing FontAwesome static files
- Extract the zip file to `mainwebsite/static/fontawesome/`
- Verify the extraction was successful

## What Gets Extracted

The FontAwesome package includes:

- **CSS files**: All FontAwesome stylesheets (all.css, brands.css, solid.css, etc.)
- **Web fonts**: Font files for all icon sets (.woff2, .woff, .ttf, .eot)
- **JavaScript**: FontAwesome JavaScript files for SVG icons
- **SVGs**: Individual SVG files for each icon
- **SCSS/Less**: Source files for customization
- **Metadata**: Icon metadata and sprite information

## Usage in Templates

After setup, you can use FontAwesome icons in your Django templates:

```html
<!-- Load FontAwesome CSS -->
{% load static %}
<link rel="stylesheet" href="{% static 'fontawesome/css/all.min.css' %}">

<!-- Use icons -->
<i class="fas fa-home"></i>
<i class="fab fa-github"></i>
<i class="far fa-envelope"></i>
```

## Updating FontAwesome

To update to a newer version of FontAwesome:

1. Download the new FontAwesome zip file
2. Replace `mainwebsite/static/fontawesome-free-6.7.2.zip` with the new version
3. Update the filename in `scripts/setup_fontawesome.py` if needed
4. Run `python scripts/setup_fontawesome.py` to test
5. Commit the new zip file to the repository

## Troubleshooting

### Missing Icons

If icons aren't displaying:
1. Check that `scripts/setup_fontawesome.py` ran successfully during build
2. Verify FontAwesome CSS is loaded in your template
3. Check browser developer tools for 404 errors on font files

### Build Failures

If the FontAwesome setup fails:
1. Ensure the zip file exists and is not corrupted
2. Check file permissions on the static directory
3. Verify Python has write access to the static directory

### Development vs Production

- **Development**: Run `python scripts/setup_fontawesome.py` manually when needed
- **Production**: FontAwesome setup runs automatically during build process

## Benefits of This Approach

1. **Complete Icon Set**: All FontAwesome icons are available, not just a subset
2. **No External Dependencies**: No need for npm, CDN, or external services
3. **Version Control**: FontAwesome version is locked and consistent
4. **Offline Support**: Works without internet connection
5. **Build Integration**: Automatic setup during deployment
6. **Clean Repository**: Only the zip file is tracked, not thousands of individual files
