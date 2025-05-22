# -*- coding: utf-8 -*-
from odoo import api, models


class HrAttendanceOvertime(models.Model):
    _inherit = "hr.attendance.overtime"

    @api.model
    def create(self, vals):
        """Override create to prevent overtime creation during biometric import"""
        if self.env.context.get("no_overtime_creation"):
            # Skip creation if we're in the biometric import process
            return self.browse()
        return super(HrAttendanceOvertime, self).create(vals)
