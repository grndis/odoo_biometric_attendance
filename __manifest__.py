# -*- coding: utf-8 -*-
{
    "name": "Biometric Device Integration",
    "version": "18.0.1.2.2",
    "category": "Human Resources",
    "summary": "Integrating Biometric Device (Model: ZKteco uFace 202) With HR"
    "Attendance (Face + Thumb)",
    "description": "This module integrates Odoo with the biometric"
    "device(Model: ZKteco uFace 202),odoo17,odoo,hr,attendance",
    "author": "Grandis",
    "company": "superuser.id",
    "maintainer": "superuser.id",
    "website": "https://superuser.id",
    "depends": ["base_setup", "hr_attendance"],
    "external_dependencies": {
        "python": ["pyzk"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/biometric_device_details_views.xml",
        "views/hr_employee_views.xml",
        "views/daily_attendance_views.xml",
        "views/biometric_device_attendance_menus.xml",
        "data/download_data.xml",
    ],
    "images": ["static/description/banner.png"],
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
