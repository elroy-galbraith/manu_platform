import os

import psycopg

HOST = os.environ.get("JMEA_DB_HOST", "localhost")
PORT = os.environ.get("JMEA_DB_PORT", "5433")
DB = os.environ.get("JMEA_DB_NAME", "jmea")

ROLE_PASSWORDS = {
    "jmea_admin": os.environ.get("JMEA_DB_ADMIN_PASSWORD", "jmea_dev_admin"),
    "app_portal": os.environ.get("APP_PORTAL_PASSWORD", "portal_dev"),
    "transform": os.environ.get("TRANSFORM_PASSWORD", "transform_dev"),
    "svc_analytics": os.environ.get("SVC_ANALYTICS_PASSWORD", "analytics_dev"),
    "svc_matching": os.environ.get("SVC_MATCHING_PASSWORD", "matching_dev"),
}


def connect(role: str) -> psycopg.Connection:
    return psycopg.connect(
        host=HOST, port=PORT, dbname=DB, user=role, password=ROLE_PASSWORDS[role]
    )
