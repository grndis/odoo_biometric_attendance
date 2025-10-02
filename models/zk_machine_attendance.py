# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ZkMachineAttendance(models.Model):
    """Model to hold data from the biometric device"""
    _name = 'zk.machine.attendance'
    _description = 'Attendance'
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """Overriding the __check_validity function for employee attendance."""
        pass

    @api.depends('check_in', 'check_out')
    def _compute_overtime_hours(self):
        """Override overtime computation to avoid model mixing issues.

        zk.machine.attendance records are raw data storage and should not
        compute overtime hours like regular hr.attendance records.
        """
        for record in self:
            record.overtime_hours = 0.0

    @api.model
    def create(self, vals):
        """Bypass hr.attendance.create validations when storing raw punches.

        This model inherits hr.attendance fields for convenience, but raw
        log storage must not trigger hr.attendance business rules. Calling the
        base Model.create avoids parent create() logic and validations.
        """
        return models.Model.create(self, vals)

    device_id_num = fields.Char(string='Biometric Device ID',
                                help="The ID of the Biometric Device")
    punch_type = fields.Selection([('0', 'Check In'), ('1', 'Check Out'),
                                   ('2', 'Break Out'), ('3', 'Break In'),
                                   ('4', 'Overtime In'), ('5', 'Overtime Out'),
                                   ('255', 'Duplicate')],
                                  string='Punching Type',
                                  help='Punching type of the attendance')
    attendance_type = fields.Selection([('1', 'Finger'), ('15', 'Face'),
                                        ('2', 'Type_2'), ('3', 'Password'),
                                        ('4', 'Card'), ('255', 'Duplicate')],
                                       string='Category',
                                       help="Attendance detecting methods")
    punching_time = fields.Datetime(string='Punching Time',
                                    help="Punching time in the device")
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help="Working address of the employee")
