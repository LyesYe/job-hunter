# Keywords derived from Lyes Khoumeri's XR/3D/Graphics profile

SEARCH_QUERIES = [
    # English
    "unity developer",
    "XR developer",
    "VR developer",
    "AR developer",
    "mixed reality developer",
    "computer graphics engineer",
    "real-time rendering",
    "shader developer",
    "spatial computing",
    "unreal engine developer",
    # French
    "développeur unity",
    "développeur XR",
    "développeur VR",
    "développeur réalité virtuelle",
    "développeur réalité augmentée",
    "développeur réalité mixte",
    "ingénieur XR",
    "informatique graphique",
    "doctorat informatique graphique",
    "thèse rendu 3D",
]

# A job must contain at least one of these to pass the filter.
# Intentionally specific — no "c++" or "c#" alone (too generic).
RELEVANCE_KEYWORDS = [
    # Engines & frameworks
    "unity", "unreal engine", "openxr", "meta xr sdk", "ar foundation", "mrtk",
    # XR / immersive
    "xr developer", "xr engineer", "xr dev",
    "vr developer", "vr engineer", "virtual reality",
    "ar developer", "ar engineer", "augmented reality",
    "mixed reality", "réalité virtuelle", "réalité augmentée", "réalité mixte",
    "spatial computing", "meta quest", "hololens", "spatial anchors", "hand tracking",
    # Computer graphics
    "computer graphics", "computer graphic", "informatique graphique",
    "shader", "glsl", "hlsl", "opengl", "vulkan", "directx",
    "rendu temps réel", "real-time rendering", "rendering engineer",
    "gaussian splatting", "point cloud", "lidar", "3d reconstruction",
    "game engine", "moteur de jeu", "3d engine",
    # Research / PhD
    "doctorat informatique", "thèse cifre", "phd computer graphics",
    "phd rendering", "thèse rendu", "laboratoire graphique",
    # Specific job titles
    "développeur unity", "développeur xr", "ingénieur xr",
    "développeur réalité", "ingénieur 3d",
]

EXCLUSION_KEYWORDS = [
    "data scientist", "machine learning", "deep learning", "nlp",
    "devops", "sysadmin", "réseaux", "cybersécurité",
    "comptable", "commercial", "vente", "marketing",
    "ressources humaines", "human resources", "juridique",
    "finance", "banque", "assurance", "immobilier",
    "médecin", "infirmier", "pharmacie",
]

LINKEDIN_GEO_ID_FRANCE = "105015875"
