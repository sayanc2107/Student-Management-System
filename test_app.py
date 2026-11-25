import asyncio
import io
import sys
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    print("=================================================================")
    print("RUNNING COMPREHENSIVE T5 ERP SYSTEM VERIFICATION")
    print("=================================================================")

    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        health_data = res.json()
        print(f"[PASS] Health check: status={health_data.get('status')}, engine={health_data.get('databaseEngine')}")

        # 2. Template root check & Branding
        res = client.get("/")
        assert res.status_code == 200, f"Root page failed: {res.status_code}"
        assert "T5 ERP SYSTEM" in res.text, "App branding 'T5 ERP SYSTEM' should be in root HTML"
        assert "sayan2008c@pthdfc" in res.text, "Teacher UPI ID 'sayan2008c@pthdfc' should be in root HTML"
        print("[PASS] Root HTML template rendered with updated branding 'T5 ERP SYSTEM' and UPI ID 'sayan2008c@pthdfc'.")

        # 3. Authentication: Teacher Login
        login_res = client.post("/api/auth/login", json={
            "email": "teacher@tuition.com",
            "password": "Teacher@123"
        })
        assert login_res.status_code == 200, f"Teacher login failed: {login_res.text}"
        teacher_token = login_res.json()["access_token"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        print("[PASS] Teacher login succeeded with JWT token.")

        # 4. Authentication: Student Login
        st_login_res = client.post("/api/auth/login", json={
            "email": "aarav.mehta@example.com",
            "password": "Student@123"
        })
        assert st_login_res.status_code == 200, f"Student login failed: {st_login_res.text}"
        student_token = st_login_res.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        aarav_id = st_login_res.json()["user"]["studentId"]
        print(f"[PASS] Student login succeeded. StudentId={aarav_id}")

        # 5. Security & Permission Enforcement
        forbidden_res = client.get("/api/dashboard/teacher", headers=student_headers)
        assert forbidden_res.status_code == 403, f"Expected 403 for student accessing teacher dashboard, got {forbidden_res.status_code}"
        print("[PASS] Server-side security: Student blocked from teacher dashboard (HTTP 403).")

        fee_forbidden = client.post("/api/fees", headers=student_headers, json={
            "studentId": aarav_id,
            "period": "Test Fee",
            "amount": 1000,
            "dueDate": "2026-12-01"
        })
        assert fee_forbidden.status_code == 403, f"Expected 403 for student creating fee, got {fee_forbidden.status_code}"
        print("[PASS] Server-side security: Student blocked from creating fee charges (HTTP 403).")

        # 6. Teacher Dashboard Metrics
        t_dash = client.get("/api/dashboard/teacher", headers=teacher_headers)
        assert t_dash.status_code == 200
        d_data = t_dash.json()
        assert "stats" in d_data
        assert d_data["stats"]["activeStudents"] >= 5
        print(f"[PASS] Teacher Dashboard metrics verified: {d_data['stats']['activeStudents']} active students, pending fees: {d_data['stats']['currency']}{d_data['stats']['totalPendingFees']}")

        # 7. Student Management CRUD & Privacy
        new_student = {
            "name": "Pranav Kulkarni",
            "grade": "Grade 11 - CBSE",
            "course": "Pure Science Intensive",
            "subjects": ["Physics", "Mathematics"],
            "email": "pranav.kulkarni@example.com",
            "mobile": "+91 99000 11223",
            "guardian": {
                "name": "Sunil Kulkarni",
                "mobile": "+91 99000 99887",
                "email": "sunil.kulkarni@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Strong in calculus and algebra."
        }
        create_st_res = client.post("/api/students", headers=teacher_headers, json=new_student)
        assert create_st_res.status_code == 201, f"Create student failed: {create_st_res.text}"
        created_id = create_st_res.json()["id"]
        print(f"[PASS] Student created by teacher. ID={created_id}")

        st_profile_view = client.get(f"/api/students/{aarav_id}", headers=student_headers)
        assert st_profile_view.status_code == 200
        aarav_profile = st_profile_view.json()
        assert "mobile" not in aarav_profile["guardian"], "Parent mobile should be redacted for student view"
        assert "email" not in aarav_profile["guardian"], "Parent email should be redacted for student view"
        print("[PASS] Privacy verification: Parent/guardian phone & email strictly redacted from student profile view.")

        # 8. Schedule, Class Modes (Online / Offline), & Calendar Month Navigation
        # 8a: Create Online Class with meeting link
        online_class_payload = {
            "title": "Wave Optics Online Masterclass",
            "subject": "Physics",
            "grade": "Grade 12",
            "mode": "Online",
            "date": "2026-11-28",
            "startTime": "16:00",
            "endTime": "17:30",
            "meetingLink": "https://meet.google.com/test-wave-optics",
            "notes": "Young's double slit derivation session",
            "assignedStudentIds": [aarav_id]
        }
        online_res = client.post("/api/classes", headers=teacher_headers, json=online_class_payload)
        assert online_res.status_code == 201
        online_class = online_res.json()
        assert online_class["mode"] == "Online"
        assert online_class["meetingLink"] == "https://meet.google.com/test-wave-optics"
        online_class_id = online_class["id"]
        print(f"[PASS] Scheduled Online class with meeting link: ID={online_class_id}")

        # 8b: Create Offline Class (meeting link must NOT be set or displayed)
        offline_class_payload = {
            "title": "Kinematics Problem Solving (In-Person)",
            "subject": "Physics",
            "grade": "Grade 11",
            "mode": "Offline",
            "date": "2026-11-29",
            "startTime": "10:00",
            "endTime": "11:30",
            "meetingLink": "https://meet.google.com/should-be-cleared",
            "notes": "Bring physical workbooks",
            "assignedStudentIds": [aarav_id]
        }
        offline_res = client.post("/api/classes", headers=teacher_headers, json=offline_class_payload)
        assert offline_res.status_code == 201
        offline_class = offline_res.json()
        assert offline_class["mode"] == "Offline"
        assert not offline_class.get("meetingLink"), "Offline class must never store or expose meeting links"
        offline_class_id = offline_class["id"]
        print(f"[PASS] Scheduled Offline class: ID={offline_class_id}, verified meetingLink is empty.")

        # 8c: Calendar Month Navigation Filter (year & month query parameters)
        month_res = client.get("/api/classes?year=2026&month=11", headers=teacher_headers)
        assert month_res.status_code == 200
        classes_nov = month_res.json()
        assert any(c["id"] == online_class_id for c in classes_nov)
        print(f"[PASS] Calendar month filter verified: returned {len(classes_nov)} classes for 2026-11.")

        # Mark bulk attendance
        att_res = client.post("/api/attendance/bulk", headers=teacher_headers, json={
            "classId": online_class_id,
            "records": [
                {"studentId": aarav_id, "status": "present", "remarks": "Very attentive"}
            ]
        })
        assert att_res.status_code == 200
        print("[PASS] Bulk attendance recorded successfully.")

        # 9. Class Remarks and Feedback
        # 9a: Student posts feedback on the class
        st_fb_res = client.post(f"/api/classes/{online_class_id}/feedback", headers=student_headers, json={
            "feedback": "Understood the fringe width formula well, but need clarification on coherent sources.",
            "sharedWithStudent": True
        })
        assert st_fb_res.status_code == 201
        st_fb_id = st_fb_res.json()["id"]
        print(f"[PASS] Student posted class feedback: ID={st_fb_id}")

        # 9b: Teacher posts private feedback (sharedWithStudent=False)
        t_fb_res = client.post(f"/api/classes/{online_class_id}/feedback", headers=teacher_headers, json={
            "feedback": "Teacher private observation: Aarav needs practice on secondary maxima derivations.",
            "studentId": aarav_id,
            "sharedWithStudent": False
        })
        assert t_fb_res.status_code == 201
        t_fb_id = t_fb_res.json()["id"]
        print(f"[PASS] Teacher posted private feedback: ID={t_fb_id}")

        # 9c: Student views feedback: must only see student's feedback, NOT teacher's private feedback
        st_view_fb = client.get(f"/api/classes/{online_class_id}/feedback", headers=student_headers)
        assert st_view_fb.status_code == 200
        fb_ids_for_student = [fb["id"] for fb in st_view_fb.json()]
        assert st_fb_id in fb_ids_for_student
        assert t_fb_id not in fb_ids_for_student, "Private teacher feedback must NOT be visible to student"
        print("[PASS] Privacy verification: Private teacher feedback is hidden from student.")

        # 9d: Teacher views feedback: sees both
        t_view_fb = client.get(f"/api/classes/{online_class_id}/feedback", headers=teacher_headers)
        assert t_view_fb.status_code == 200
        assert len(t_view_fb.json()) >= 2
        print("[PASS] Teacher can view all feedback entries.")

        # 9e: Teacher toggles share: now student can see it
        share_toggle_res = client.put(f"/api/classes/feedback/{t_fb_id}/share", headers=teacher_headers)
        assert share_toggle_res.status_code == 200
        assert share_toggle_res.json()["sharedWithStudent"] is True
        
        st_view_fb_after = client.get(f"/api/classes/{online_class_id}/feedback", headers=student_headers)
        assert t_fb_id in [fb["id"] for fb in st_view_fb_after.json()], "Shared teacher feedback should now be visible to student"
        print("[PASS] Teacher toggled feedback sharing; student can now view the remark.")

        # 10. Homework Submissions with Multi-Format File Upload (.c, .java, .pdf, etc.)
        # 10a: Upload a .c file
        c_code_content = b'#include <stdio.h>\nint main() { printf("Hello YDSE\\n"); return 0; }\n'
        upload_c_res = client.post(
            "/api/homework/upload",
            headers=student_headers,
            files={"file": ("solution.c", io.BytesIO(c_code_content), "text/x-c")}
        )
        assert upload_c_res.status_code == 200, f"Upload .c file failed: {upload_c_res.text}"
        c_upload_data = upload_c_res.json()
        assert c_upload_data["url"].endswith(".c")
        print(f"[PASS] Successfully uploaded .c code solution: {c_upload_data['filename']} ({c_upload_data['sizeFormatted']})")

        # 10b: Upload a .java file
        java_code_content = b'public class Solution { public static void main(String[] args) {} }\n'
        upload_java_res = client.post(
            "/api/homework/upload",
            headers=student_headers,
            files={"file": ("Solution.java", io.BytesIO(java_code_content), "text/x-java-source")}
        )
        assert upload_java_res.status_code == 200, f"Upload .java file failed: {upload_java_res.text}"
        java_upload_data = upload_java_res.json()
        assert java_upload_data["url"].endswith(".java")
        print(f"[PASS] Successfully uploaded .java solution: {java_upload_data['filename']}")

        # 10c: Create homework and submit using uploaded file
        hw_payload = {
            "title": "Wave Optics Programming & Derivations",
            "subject": "Physics",
            "instructions": "Submit numerical code or analytical derivations.",
            "assignedStudentIds": [aarav_id],
            "dueDate": "2026-11-30",
            "totalMarks": 25
        }
        hw_res = client.post("/api/homework", headers=teacher_headers, json=hw_payload)
        assert hw_res.status_code == 201
        new_hw_id = hw_res.json()["id"]

        sub_res = client.post("/api/homework/submit", headers=student_headers, json={
            "homeworkId": new_hw_id,
            "submissionText": "Uploaded C implementation calculating optical path differences.",
            "attachmentUrl": c_upload_data["url"],
            "attachmentName": "solution.c"
        })
        assert sub_res.status_code == 200
        sub_id = sub_res.json()["id"]
        print(f"[PASS] Student submitted homework with uploaded .c file: SubID={sub_id}")

        # Teacher reviews submission
        rev_res = client.post(f"/api/homework/submissions/{sub_id}/review", headers=teacher_headers, json={
            "grade": "25/25",
            "feedback": "Excellent C solution with proper float precision."
        })
        assert rev_res.status_code == 200
        assert rev_res.json()["status"] == "reviewed"
        print(f"[PASS] Teacher reviewed submission: Grade={rev_res.json()['grade']}")

        # 11. Password Management
        # 11a: Teacher sets a student's password
        set_pw_res = client.post(f"/api/students/{aarav_id}/set-password", headers=teacher_headers, json={
            "newPassword": "NewAaravPassword@2026"
        })
        assert set_pw_res.status_code == 200
        print("[PASS] Teacher set student password successfully.")

        # 11b: Student logs in with the teacher-set password
        new_login_res = client.post("/api/auth/login", json={
            "email": "aarav.mehta@example.com",
            "password": "NewAaravPassword@2026"
        })
        assert new_login_res.status_code == 200, f"Login with teacher-set password failed: {new_login_res.text}"
        new_st_token = new_login_res.json()["access_token"]
        new_st_headers = {"Authorization": f"Bearer {new_st_token}"}
        print("[PASS] Student successfully authenticated with teacher-set password.")

        # 11c: Student changes own password while signed in
        st_change_res = client.post("/api/auth/change-password", headers=new_st_headers, json={
            "currentPassword": "NewAaravPassword@2026",
            "newPassword": "StudentSelfPassword@2026"
        })
        assert st_change_res.status_code == 200
        print("[PASS] Student changed own password successfully.")

        # Verify student logs in with student-changed password
        st_login_changed = client.post("/api/auth/login", json={
            "email": "aarav.mehta@example.com",
            "password": "StudentSelfPassword@2026"
        })
        assert st_login_changed.status_code == 200
        print("[PASS] Student successfully authenticated with student-changed password.")

        # 11d: Restore student's password to original Student@123 for consistency
        client.post(f"/api/students/{aarav_id}/set-password", headers=teacher_headers, json={
            "newPassword": "Student@123"
        })

        # 11e: Security: Student cannot set another student's password
        st_forbidden_pw = client.post(f"/api/students/{created_id}/set-password", headers=student_headers, json={
            "newPassword": "HackedPassword@123"
        })
        assert st_forbidden_pw.status_code == 403, "Student must not be allowed to set passwords"
        print("[PASS] Server-side security: Student blocked from setting passwords (HTTP 403).")

        # 12. Exams with Google Form Link
        exam_res = client.post("/api/exams", headers=teacher_headers, json={
            "title": "Term 2 Physics Assessment",
            "subject": "Physics",
            "grade": "Grade 12",
            "date": "2026-12-05",
            "startTime": "11:00",
            "durationMinutes": 60,
            "totalMarks": 50,
            "syllabus": "Ray Optics and Wave Optics",
            "formLink": "https://forms.gle/sample-optics-assessment"
        })
        assert exam_res.status_code == 201
        print("[PASS] Created exam with Google Form link.")

        # 13. Fees, Direct UPI & Reversals
        contact_res = client.get("/api/settings/contact")
        assert contact_res.status_code == 200
        contact_data = contact_res.json()
        assert contact_data["teacherUpiId"] == "sayan2008c@pthdfc", f"Expected UPI ID sayan2008c@pthdfc, got {contact_data['teacherUpiId']}"
        print(f"[PASS] Direct UPI details verified: UPI ID = {contact_data['teacherUpiId']}")

        # Create fee charge
        fee_res = client.post("/api/fees", headers=teacher_headers, json={
            "studentId": created_id,
            "period": "December 2026 Tuition",
            "amount": 3500.0,
            "dueDate": "2026-12-05",
            "description": "Tuition for 8 sessions"
        })
        assert fee_res.status_code == 201
        created_fee_id = fee_res.json()["id"]

        # Teacher records manual payment
        pay_res = client.post("/api/fees/payments", headers=teacher_headers, json={
            "studentId": created_id,
            "feeId": created_fee_id,
            "amount": 2000.0,
            "paidAt": "2026-11-25",
            "method": "upi",
            "reference": "UPI/sayan2008c@pthdfc/98765412",
            "note": "Direct UPI received at sayan2008c@pthdfc"
        })
        assert pay_res.status_code == 201
        payment_id = pay_res.json()["id"]

        # Check ledger balance
        ledger = client.get(f"/api/fees/student/{created_id}/summary", headers=teacher_headers)
        assert ledger.json()["balance"] == 1500.0
        assert ledger.json()["totalPaid"] == 2000.0
        print("[PASS] Manual payment recording & balance ledger verified.")

        # Payment Reversal
        rev_pay_res = client.post("/api/fees/payments/reverse", headers=teacher_headers, json={
            "paymentId": payment_id,
            "reason": "Test reversal audit"
        })
        assert rev_pay_res.status_code == 200
        ledger_after_rev = client.get(f"/api/fees/student/{created_id}/summary", headers=teacher_headers)
        assert ledger_after_rev.json()["balance"] == 3500.0
        print("[PASS] Payment reversal verified: balance restored, audit trail preserved.")

        # 14. Dual Authentication: Username and Email Both Supported
        # 14a. Student login with Username "aarav"
        aarav_username_login = client.post("/api/auth/login", json={
            "email": "aarav",
            "password": "Student@123"
        })
        assert aarav_username_login.status_code == 200, f"Login with username 'aarav' failed: {aarav_username_login.text}"
        assert aarav_username_login.json()["user"]["username"] == "aarav"
        print("[PASS] Dual login: Student logged in successfully using username 'aarav'.")

        # 14b. Teacher login with Username "teacher"
        teacher_username_login = client.post("/api/auth/login", json={
            "email": "teacher",
            "password": "Teacher@123"
        })
        assert teacher_username_login.status_code == 200, f"Login with username 'teacher' failed: {teacher_username_login.text}"
        assert teacher_username_login.json()["user"]["role"] == "teacher"
        print("[PASS] Dual login: Teacher logged in successfully using username 'teacher'.")

        # 14c. Teacher creates a new student with a custom username
        custom_student_payload = {
            "name": "Ishan Sharma",
            "username": "ishan_2026",
            "grade": "Grade 10 - ICSE",
            "course": "Foundation Science",
            "subjects": ["Physics", "Chemistry"],
            "email": "ishan.sharma@example.com",
            "mobile": "+91 98888 77665",
            "guardian": {
                "name": "Rajesh Sharma",
                "mobile": "+91 98888 11223",
                "email": "rajesh.sharma@example.com",
                "relationship": "Father"
            },
            "enrollmentStatus": "active",
            "notes": "Custom username test student."
        }
        create_custom_st_res = client.post("/api/students", headers=teacher_headers, json=custom_student_payload)
        assert create_custom_st_res.status_code == 201, f"Create student with custom username failed: {create_custom_st_res.text}"
        custom_st_data = create_custom_st_res.json()
        assert custom_st_data["username"] == "ishan_2026"
        print(f"[PASS] Teacher added student with custom username 'ishan_2026' (ID={custom_st_data['id']}).")

        # Set password for the new student
        set_pw_res = client.post(f"/api/students/{custom_st_data['id']}/set-password", headers=teacher_headers, json={
            "newPassword": "IshanPassword@123"
        })
        assert set_pw_res.status_code == 200

        # Login using username "ishan_2026"
        ishan_user_login = client.post("/api/auth/login", json={
            "email": "ishan_2026",
            "password": "IshanPassword@123"
        })
        assert ishan_user_login.status_code == 200, f"Login via username failed: {ishan_user_login.text}"
        print("[PASS] New student logged in successfully using username 'ishan_2026'.")

        # Login using email "ishan.sharma@example.com"
        ishan_email_login = client.post("/api/auth/login", json={
            "email": "ishan.sharma@example.com",
            "password": "IshanPassword@123"
        })
        assert ishan_email_login.status_code == 200, f"Login via email failed: {ishan_email_login.text}"
        print("[PASS] New student logged in successfully using email 'ishan.sharma@example.com'.")

        # 15. Teacher Records Payment for the new student
        # Create fee for Ishan
        ishan_fee_res = client.post("/api/fees", headers=teacher_headers, json={
            "studentId": custom_st_data["id"],
            "period": "Registration & Term 1",
            "amount": 5000.0,
            "dueDate": "2026-12-10",
            "description": "Tuition enrollment fee"
        })
        assert ishan_fee_res.status_code == 201
        ishan_fee_id = ishan_fee_res.json()["id"]

        # Teacher records payment
        ishan_pay_res = client.post("/api/fees/payments", headers=teacher_headers, json={
            "studentId": custom_st_data["id"],
            "feeId": ishan_fee_id,
            "amount": 5000.0,
            "paidAt": "2026-11-25",
            "method": "upi",
            "reference": "UPI/sayan2008c@pthdfc/998877",
            "note": "Paid in full via UPI"
        })
        assert ishan_pay_res.status_code == 201

        # Check balance is 0 and totalPaid is 5000.0
        ishan_summary = client.get(f"/api/fees/student/{custom_st_data['id']}/summary", headers=teacher_headers)
        assert ishan_summary.status_code == 200
        assert ishan_summary.json()["balance"] == 0.0
        assert ishan_summary.json()["totalPaid"] == 5000.0
        assert ishan_summary.json()["totalFees"] == 5000.0
        print("[PASS] Payment recorded by teacher: balance settled in full (balance=0.0, totalPaid=5000.0).")

        # 16. Dedicated Student Assignment for Online Class Sessions & Privacy Preservation
        # Login student Diya (Student B) and Kabir (Student C)
        diya_login = client.post("/api/auth/login", json={"email": "diya", "password": "Student@123"})
        assert diya_login.status_code == 200
        diya_token = diya_login.json()["access_token"]
        diya_headers = {"Authorization": f"Bearer {diya_token}"}
        diya_id = diya_login.json()["user"]["studentId"]

        kabir_login = client.post("/api/auth/login", json={"email": "kabir", "password": "Student@123"})
        assert kabir_login.status_code == 200
        kabir_token = kabir_login.json()["access_token"]
        kabir_headers = {"Authorization": f"Bearer {kabir_token}"}
        kabir_id = kabir_login.json()["user"]["studentId"]

        # Teacher schedules an Online class assigned specifically to Aarav and Diya (NOT Kabir)
        dedicated_class_res = client.post("/api/classes", headers=teacher_headers, json={
            "title": "Quantum Physics Masterclass",
            "subject": "Physics",
            "grade": "Grade 12",
            "mode": "Online",
            "date": "2026-11-28",
            "startTime": "18:00",
            "endTime": "19:30",
            "meetingLink": "https://meet.google.com/qnt-phys-101",
            "notes": "Dedicated session for selected students",
            "assignedStudentIds": [aarav_id, diya_id]
        })
        assert dedicated_class_res.status_code == 201
        ded_class_id = dedicated_class_res.json()["id"]

        # 16a. Aarav (assigned) checks dashboard & classes
        aarav_dash = client.get("/api/dashboard/student", headers=student_headers)
        aarav_classes = [c["id"] for c in aarav_dash.json().get("upcomingClasses", [])]
        assert ded_class_id in aarav_classes, "Aarav must see dedicated class in dashboard"

        aarav_class_detail = client.get(f"/api/classes/{ded_class_id}", headers=student_headers)
        assert aarav_class_detail.status_code == 200
        # Verify student privacy: Aarav can only see their own name
        assert aarav_class_detail.json()["assignedStudentNames"] == ["Aarav Mehta"], "Aarav must only see their own name"
        assert diya_id not in aarav_class_detail.json().get("assignedStudentIds", []), "Other students' IDs must be redacted for student"

        # 16b. Diya (assigned) checks dashboard & classes
        diya_dash = client.get("/api/dashboard/student", headers=diya_headers)
        diya_classes = [c["id"] for c in diya_dash.json().get("upcomingClasses", [])]
        assert ded_class_id in diya_classes, "Diya must see dedicated class in dashboard"

        diya_class_detail = client.get(f"/api/classes/{ded_class_id}", headers=diya_headers)
        assert diya_class_detail.status_code == 200
        assert diya_class_detail.json()["assignedStudentNames"] == ["Diya Sen"], "Diya must only see their own name"
        assert aarav_id not in diya_class_detail.json().get("assignedStudentIds", []), "Other students' IDs must be redacted for student"

        # 16c. Kabir (NOT assigned) checks dashboard & classes
        kabir_dash = client.get("/api/dashboard/student", headers=kabir_headers)
        kabir_classes = [c["id"] for c in kabir_dash.json().get("upcomingClasses", [])]
        assert ded_class_id not in kabir_classes, "Kabir must NOT see dedicated class in dashboard"

        kabir_class_forbidden = client.get(f"/api/classes/{ded_class_id}", headers=kabir_headers)
        assert kabir_class_forbidden.status_code == 403, "Unassigned student must receive 403 Forbidden"
        print("[PASS] Dedicated Online class session assignment & student privacy verified.")

        # 17. Dedicated Student Homework Assignment & Submissions with Names
        # Teacher creates homework assigned ONLY to Aarav
        ded_hw_res = client.post("/api/homework", headers=teacher_headers, json={
            "title": "Special Relativity Advanced Problems",
            "subject": "Physics",
            "instructions": "Solve Lorentz transformation problems 1-5",
            "totalMarks": 50,
            "dueDate": "2026-11-30",
            "assignedStudentIds": [aarav_id]
        })
        assert ded_hw_res.status_code == 201
        ded_hw_id = ded_hw_res.json()["id"]

        # 17a. Aarav checks homework list & dashboard
        aarav_hw_list = client.get("/api/homework", headers=student_headers)
        aarav_hw_ids = [h["id"] for h in aarav_hw_list.json()]
        assert ded_hw_id in aarav_hw_ids, "Aarav must see assigned dedicated homework"

        # 17b. Diya (unassigned) checks homework list
        diya_hw_list = client.get("/api/homework", headers=diya_headers)
        diya_hw_ids = [h["id"] for h in diya_hw_list.json()]
        assert ded_hw_id not in diya_hw_ids, "Diya must NOT see unassigned homework"

        diya_hw_detail = client.get(f"/api/homework/{ded_hw_id}", headers=diya_headers)
        assert diya_hw_detail.status_code == 403, "Unassigned student must receive 403 Forbidden for homework"

        # 17c. Aarav submits a solution file
        aarav_sub_res = client.post("/api/homework/submit", headers=student_headers, json={
            "homeworkId": ded_hw_id,
            "submissionText": "Detailed Minkowski spacetime derivations attached.",
            "attachmentUrl": "/static/uploads/submissions/aarav_relativity.c",
            "attachmentName": "lorentz_transform.c"
        })
        assert aarav_sub_res.status_code == 200

        # 17d. Teacher checks submissions: verifies student's name is beside the file
        hw_subs_res = client.get(f"/api/homework/{ded_hw_id}/submissions", headers=teacher_headers)
        assert hw_subs_res.status_code == 200
        subs_list = hw_subs_res.json()
        assert len(subs_list) == 1
        assert subs_list[0]["studentName"] == "Aarav Mehta"
        assert subs_list[0]["attachmentName"] == "lorentz_transform.c"
        print(f"[PASS] Homework submission verified with student name beside file: {subs_list[0]['studentName']} • {subs_list[0]['attachmentName']}")

        print("=================================================================")
        print("ALL 17 COMPREHENSIVE VERIFICATION SUITES PASSED SUCCESSFULLY!")
        print("=================================================================")

if __name__ == "__main__":
    run_tests()
