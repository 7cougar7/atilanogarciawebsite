"""
Single source of truth for static homepage content that is both server-rendered (for
SEO / no-JS) and handed to React islands as props. Previously this data was duplicated
inline across two responsive copies in homepage.html.
"""

PROJECTS = [
    {
        "name": "Personal Website",
        "label": "Project 1: This Website!",
        "url": "https://github.com/7cougar7/atilanogarciawebsite",
    },
    {
        "name": "Spotify API",
        "label": "Project 2: Exploration of the Spotify API",
        "url": "https://github.com/7cougar7/spotify-api-test",
    },
    {
        "name": "Football Predictor",
        "label": "Project 3: Ultimate AI Football Predictor",
        "url": "https://github.com/7cougar7/ultimate-football-predictor",
    },
    {
        "name": "AR Map Generator",
        "label": "Project 4: Augmented Reality Map Generator",
        "url": "https://github.com/7cougar7/pearlinlab",
    },
    {
        "name": "Machine Learning",
        "label": "Project 5: Exploration of Machine Learning",
        "url": "https://github.com/7cougar7/machine-learning-learning",
    },
]

VIEW_MORE_URL = "https://github.com/7cougar7/machine-learning-learning"

SOCIALS = [
    {
        "platform": "LinkedIn",
        "url": "https://www.linkedin.com/in/atilano-garcia/",
        "icon": "fa-brands fa-linkedin",
    },
    {
        "platform": "GitHub",
        "url": "https://www.github.com/7cougar7",
        "icon": "fab fa-github",
    },
    {
        "platform": "Instagram",
        "url": "https://www.instagram.com/tilo.g_",
        "icon": "fa-brands fa-instagram",
    },
    {
        "platform": "X",
        "url": "https://twitter.com/tilo_g__",
        "icon": "fa-brands fa-x-twitter",
    },
]


def homepage_content_context():
    """Context fragment for the homepage: server-render data + island prop blobs."""
    return {
        "projects": PROJECTS,
        "socials": SOCIALS,
        "view_more_url": VIEW_MORE_URL,
        "projectlist_props": {"projects": PROJECTS, "viewMoreUrl": VIEW_MORE_URL},
        "sociallinks_props": {"socials": SOCIALS},
    }
