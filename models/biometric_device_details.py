# -*- coding: utf-8 -*-
import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""

    _name = "biometric.device.details"
    _description = "Biometric Device Details"

    name = fields.Char(string="Name", required=True, help="Record Name")
    device_ip = fields.Char(
        string="Device IP", required=True, help="The IP address of the Device"
    )
    port_number = fields.Integer(
        string="Port Number", required=True, help="The Port Number of the Device"
    )
    address_id = fields.Many2one(
        "res.partner", string="Working Address", help="Working address of the partner"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
        help="Current Company",
    )

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(
            self.device_ip,
            port=self.port_number,
            timeout=30,
            password=False,
            ommit_ping=False,
        )
        try:
            if zk.connect():
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": "Successfully Connected",
                        "type": "success",
                        "sticky": False,
                    },
                }
        except Exception as error:
            raise ValidationError(f"{error}")

    def action_set_timezone(self):
        """Function to set user's timezone to device"""
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(
                    machine_ip,
                    port=zk_port,
                    timeout=15,
                    password=0,
                    force_udp=False,
                    ommit_ping=False,
                )
            except NameError:
                raise UserError(
                    _(
                        "Pyzk module not Found. Please install it"
                        "with 'pip3 install pyzk'."
                    )
                )
            conn = self.device_connect(zk)
            if conn:
                user_tz = self.env.context.get("tz") or self.env.user.tz or "UTC"
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz)
                )
                conn.set_time(user_timezone_time)
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": "Successfully Set the Time",
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise UserError(_("Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(
                        machine_ip,
                        port=zk_port,
                        timeout=30,
                        password=0,
                        force_udp=False,
                        ommit_ping=False,
                    )
                except NameError:
                    raise UserError(_("Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute("""delete from zk_machine_attendance""")
                        conn.disconnect()
                    else:
                        raise UserError(
                            _(
                                "Unable to clear Attendance log.Are you sure "
                                "attendance log is not empty."
                            )
                        )
                else:
                    raise UserError(
                        _(
                            "Unable to connect to Attendance Device. Please use "
                            "Test Connection button to verify."
                        )
                    )
            except Exception as error:
                raise ValidationError(f"{error}")

    @api.model
    def cron_download(self):
        machines = self.env["biometric.device.details"].search([])
        for machine in machines:
            machine.action_download_attendance()

    ### Action Download Attendance
    def action_download_attendance(self):
        """Function to download attendance records from the device"""
        _logger.info("++++++++++++Cron Executed++++++++++++++++++++++")

        # Process in smaller batches to avoid long transactions
        max_records_per_batch = 50

        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number

            # Connect to the device
            try:
                zk = ZK(
                    machine_ip,
                    port=zk_port,
                    timeout=15,
                    password=0,
                    force_udp=False,
                    ommit_ping=False,
                )
            except NameError:
                raise UserError(
                    _(
                        "Pyzk module not Found. Please install it"
                        "with 'pip3 install pyzk'."
                    )
                )

            conn = self.device_connect(zk)
            if not conn:
                raise UserError(
                    _(
                        "Unable to connect, please check the"
                        "parameters and network connections."
                    )
                )

            try:
                # Set timezone
                self.action_set_timezone()

                # Disable device during download
                conn.disable_device()

                # Get users and attendance
                user = conn.get_users()
                attendance = conn.get_attendance()

                if not attendance:
                    conn.enable_device()
                    conn.disconnect()
                    raise UserError(
                        _("Unable to get the attendance log, please try again later.")
                    )

                # Process attendance in batches
                total_records = len(attendance)
                _logger.info(f"Found {total_records} attendance records to process")

                for i in range(0, total_records, max_records_per_batch):
                    # Create a new cursor for each batch to avoid long transactions
                    with self.env.cr.savepoint():
                        batch = attendance[i : i + max_records_per_batch]
                        _logger.info(
                            f"Processing batch {i//max_records_per_batch + 1} with {len(batch)} records"
                        )

                        self._process_attendance_batch(batch, user, info)

                # Enable device and disconnect
                conn.enable_device()
                conn.disconnect()

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": f"Successfully processed {total_records} attendance records",
                        "type": "success",
                        "sticky": False,
                    },
                }

            except Exception as e:
                _logger.error(f"Error in download_attendance: {e}")
                # Make sure to enable the device and disconnect even if there's an error
                try:
                    if conn:
                        conn.enable_device()
                        conn.disconnect()
                except Exception:
                    pass

                raise UserError(_(f"Error processing attendance: {e}"))

        def _process_attendance_batch(self, batch, user, info):
            """Process a batch of attendance records"""
            zk_attendance = self.env["zk.machine.attendance"]
            hr_attendance = self.env["hr.attendance"]

            for each in batch:
                try:
                    # Convert timestamp to UTC
                    atten_time = each.timestamp
                    local_tz = pytz.timezone(self.env.user.partner_id.tz or "GMT")
                    local_dt = local_tz.localize(atten_time, is_dst=None)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                    atten_time = datetime.datetime.strptime(utc_dt, "%Y-%m-%d %H:%M:%S")

                    # Find the user
                    user_found = False
                    for uid in user:
                        if uid.user_id == each.user_id:
                            user_found = True
                            get_user_id = self.env["hr.employee"].search(
                                [("device_id_num", "=", each.user_id)]
                            )

                            if not get_user_id:
                                # Create new employee if not found
                                get_user_id = self.env["hr.employee"].create(
                                    {
                                        "device_id_num": each.user_id,
                                        "name": uid.name,
                                    }
                                )

                            # Check for duplicate attendance
                            duplicate_atten_ids = zk_attendance.search(
                                [
                                    ("device_id_num", "=", each.user_id),
                                    ("punching_time", "=", atten_time),
                                ]
                            )

                            if duplicate_atten_ids:
                                _logger.info(
                                    f"Skipping duplicate attendance for {each.user_id} at {atten_time}"
                                )
                                continue

                            # Map punch types
                            original_punch = str(each.punch)
                            effective_punch = original_punch

                            # Map overtime punches to regular punches
                            if original_punch == "4":  # Overtime In
                                effective_punch = "0"  # Map to Check In
                            elif original_punch == "5":  # Overtime Out
                                effective_punch = "1"  # Map to Check Out

                            # Create zk_attendance record
                            zk_attendance.create(
                                {
                                    "employee_id": get_user_id.id,
                                    "device_id_num": each.user_id,
                                    "attendance_type": str(each.status),
                                    "punch_type": original_punch,
                                    "punching_time": atten_time,
                                    "address_id": info.address_id.id,
                                }
                            )

                            # Process based on effective punch type
                            if effective_punch == "0":  # Check In
                                self._process_check_in(
                                    hr_attendance, get_user_id, atten_time
                                )
                            elif effective_punch == "1":  # Check Out
                                self._process_check_out(
                                    hr_attendance, get_user_id, atten_time
                                )

                            break  # Found the user, no need to continue the loop

                    if not user_found:
                        _logger.warning(
                            f"User ID {each.user_id} not found in device users"
                        )

                except Exception as e:
                    _logger.error(f"Error processing attendance record: {e}")
                    # Continue with next record instead of failing the entire batch
                    continue

        def _process_check_in(self, hr_attendance, employee, atten_time):
            """Process a check-in punch"""
            try:
                # Find if there's an open attendance record
                open_attendance = hr_attendance.search(
                    [("employee_id", "=", employee.id), ("check_out", "=", False)],
                    limit=1,
                )

                if open_attendance:
                    # If there's an open attendance, close it first
                    open_attendance.write({"check_out": atten_time})

                # Create a new check-in
                hr_attendance.create(
                    {
                        "employee_id": employee.id,
                        "check_in": atten_time,
                    }
                )

            except Exception as e:
                _logger.error(
                    f"Error processing check-in for employee {employee.name}: {e}"
                )

        def _process_check_out(self, hr_attendance, employee, atten_time):
            """Process a check-out punch"""
            try:
                # Find if there's an open attendance record
                open_attendance = hr_attendance.search(
                    [("employee_id", "=", employee.id), ("check_out", "=", False)],
                    limit=1,
                )

                if open_attendance:
                    # If there's an open attendance, close it
                    open_attendance.write({"check_out": atten_time})
                else:
                    # No open attendance to close
                    # Find the last attendance record
                    last_attendance = hr_attendance.search(
                        [("employee_id", "=", employee.id)],
                        order="check_in desc",
                        limit=1,
                    )

                    if last_attendance and last_attendance.check_out:
                        # Check if the last check-out was recent (within 3 minutes)
                        time_diff = atten_time - last_attendance.check_out

                        if time_diff.total_seconds() <= 180:
                            # Create a short attendance span
                            hr_attendance.create(
                                {
                                    "employee_id": employee.id,
                                    "check_in": last_attendance.check_out,
                                    "check_out": atten_time,
                                }
                            )
                        else:
                            # Create a new check-in instead
                            hr_attendance.create(
                                {
                                    "employee_id": employee.id,
                                    "check_in": atten_time,
                                }
                            )
                    else:
                        # No previous attendance with check-out, create a check-in
                        hr_attendance.create(
                            {
                                "employee_id": employee.id,
                                "check_in": atten_time,
                            }
                        )

            except Exception as e:
                _logger.error(
                    f"Error processing check-out for employee {employee.name}: {e}"
                )

    ### Action restart device
    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(
            self.device_ip,
            port=self.port_number,
            timeout=15,
            password=0,
            force_udp=False,
            ommit_ping=False,
        )
        self.device_connect(zk).restart()
