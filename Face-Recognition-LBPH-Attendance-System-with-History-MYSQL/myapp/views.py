from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
import cv2
import numpy as np
from PIL import Image 
import os
import pandas as pd
import xlwt
from xlwt import Workbook
from datetime import datetime
import mysql.connector
import time 
import pyttsx3
import threading
import winsound


date = datetime.today().strftime('%Y-%m-%d')
engine = pyttsx3.init()

def beep():
    winsound.Beep(1000, 500)

def speak_message(message):
    engine.say(message)
    engine.runAndWait()

def speak_message_threaded(message):
    time.sleep(1)
    thread = threading.Thread(target=speak_message, args=(message,))
    thread.start()

def beep_and_speak(message):
    beep_thread = threading.Thread(target=beep)
    speak_thread = threading.Thread(target=lambda: speak_message_threaded(message))
    beep_thread.start()
    speak_thread.start()
    beep_thread.join()  # Ensure beep completes before finishing
    speak_thread.join()  # Ensure speech completes before finishing

# Database connection setup
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="tiger",
    database="FaceRecognitionDB"
)
cursor = connection.cursor()

def index(request):
    if request.method == "POST":
        all_names = {}

        def faceRecognition():
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read('trainer/trainer.yml')
            cascadePath = "haarcascade_frontalface_default.xml"
            faceCascade = cv2.CascadeClassifier(cascadePath)
            font = cv2.FONT_HERSHEY_SIMPLEX

            # Starting realtime video capture
            cam = cv2.VideoCapture(0)
            cam.set(3, 640)  # set video width
            cam.set(4, 480)  # set video height

            # Define min window size to be recognized as a face
            minW = 0.1 * cam.get(3)
            minH = 0.1 * cam.get(4)

            cursor.execute("SELECT name FROM Names")
            result = cursor.fetchall()
            names = [row[0] for row in result]
            print(names)

            t0 = time.time()
            while True:
                ret, img = cam.read()
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                faces = faceCascade.detectMultiScale(
                    gray,
                    scaleFactor=1.2,
                    minNeighbors=5,
                    minSize=(int(minW), int(minH)),
                )

                for (x, y, w, h) in faces:
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    id, confidence = recognizer.predict(gray[y:y + h, x:x + w])

                    if confidence < 100:
                        id = names[id]
                        confidence = "  {0}%".format(round(100 - confidence))

                        if id != "unknown" and id not in all_names and int(confidence[:-1].strip()) > 25:
                            now = datetime.now()
                            current_time = now.strftime("%H:%M:%S")
                            all_names[id] = current_time

                            audiomessage = f"{id} your attendance has been submitted successfully"
                            beep_and_speak(audiomessage)

                    else:
                        id = "unknown"
                        confidence = "  {0}%".format(round(100 - confidence))

                    cv2.putText(img, str(id), (x + 5, y - 5), font, 1, (255, 255, 255), 2)
                    cv2.putText(img, str(confidence), (x + 5, y + h - 5), font, 1, (255, 255, 0), 1)

                cv2.imshow('camera', img)

                t1 = time.time()
                total = t1 - t0

                if total > 120.0:
                    break

                k = cv2.waitKey(10) & 0xff  # Press 'ESC' for exiting video
                if k == 27:
                    break

            cam.release()
            cv2.destroyAllWindows()

        if 'attendance' in request.POST:
            faceRecognition()
            print("all_names :" + str(all_names))

            cursor.execute("SELECT * FROM Attendance")
            result = cursor.fetchall()
            attendanceAllData = {
                row[0]: {
                    "StudentID": row[0],
                    "StudentName": row[1],
                    "Status": row[2],
                    "Date": row[3],
                    "EntryTime": row[4],
                }
                for row in result
            }

            student_all_registered_ids = [i for i in attendanceAllData]

            # Insert or Update Attendance Records
            today_date = datetime.today().strftime('%Y-%m-%d')
            for student_id, data in attendanceAllData.items():
                if data["StudentName"] in all_names:
                    cursor.execute("""
                        INSERT INTO Attendance (student_id, student_name, status, date, entry_time)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            status = VALUES(status),
                            date = VALUES(date),
                            entry_time = VALUES(entry_time)
                    """, (
                        student_id,
                        data["StudentName"],
                        "Present",
                        today_date,
                        all_names.get(data["StudentName"], None)
                    ))

            connection.commit()

        if 'attendancehistory' in request.POST:
            return redirect('attendancehistory')

    return render(request, "index.html")

def faceRegistration(request):
    def faceSampling(studentname):
        cam = cv2.VideoCapture(0)
        cam.set(3, 640)  # set video width
        cam.set(4, 480)  # set video height

        face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

        cursor.execute("SELECT name FROM Names")
        result = cursor.fetchall()
        names = [row[0] for row in result]

        studentname = studentname.lower()
        names.append(studentname)
        id = names.index(studentname)

        count = 0

        while True:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                count += 1

                cv2.imwrite("dataset/" + studentname + "." + str(id) + '.' + str(count) + ".jpg", gray[y:y + h, x:x + w])
                cv2.imshow('image', img)

            k = cv2.waitKey(100) & 0xff  # Press 'ESC' for exiting video
            if k == 27:
                break
            elif count >= 80:  # Take 80 face samples and stop video
                break

        cursor.execute("INSERT INTO Names (name) VALUES (%s)", (studentname,))
        connection.commit()

        cam.release()
        cv2.destroyAllWindows()

    def faceLearning():
        path = 'dataset'

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

        def getImagesAndLabels(path):
            imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
            faceSamples = []
            ids = []

            for imagePath in imagePaths:
                PIL_img = Image.open(imagePath).convert('L')
                img_numpy = np.array(PIL_img, 'uint8')

                id = int(os.path.split(imagePath)[-1].split(".")[1])
                faces = detector.detectMultiScale(img_numpy)

                for (x, y, w, h) in faces:
                    faceSamples.append(img_numpy[y:y + h, x:x + w])
                    ids.append(id)

            return faceSamples, ids

        faces, ids = getImagesAndLabels(path)
        recognizer.train(faces, np.array(ids))
        recognizer.write('trainer/trainer.yml')

    if request.method == "POST":
        studentid = request.POST.get('studentid')
        studentname = request.POST.get('studentname')

        cursor.execute("SELECT student_id FROM Attendance")
        result = cursor.fetchall()
        allStudentIDS = [row[0] for row in result]

        if studentid in allStudentIDS:
            return render(request, "faceRegistration.html", context={"mymessage": "Face already registered with this ID!", "Flag": "True"})
        else:
            faceSampling(studentname)
            faceLearning()

            # Ensure that date is set to today's date
            today_date = datetime.today().strftime('%Y-%m-%d')

            cursor.execute("""
                INSERT INTO Attendance (student_id, student_name, status, date, entry_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                studentid,
                studentname.lower(),
                'NA',  # Default status
                today_date,  # Ensure date is set
                None   # No entry time available at registration
            ))
            connection.commit()

            return render(request, "faceRegistration.html", context={"mymessage": "Face Registration Completed!", "Flag": "True", "Navigate": "True"})

    return render(request, 'faceRegistration.html')

def adminpanel(request):
    username = request.POST.get("adminusername")
    password = request.POST.get("adminpassword")

    if request.method == "POST":
        if username == "admin" and password == "admin":
            return redirect('admindashboard')
        else:
            return render(request, 'adminpanel.html', context={"mymessage": "Please check your credentials.", "Flag": "True"})
    
    return render(request, 'adminpanel.html')

def admindashboard(request):

    if 'registration' in request.POST:
            return redirect('faceRegistration')

    if 'viewStudentDetails' in request.POST:
            return redirect('student_details')

    if 'generatereport' in request.POST:
        cursor.execute("SELECT * FROM Attendance")
        result = cursor.fetchall()

        if result:
            # Create a new Excel workbook and sheet
            wb = Workbook()
            sheet1 = wb.add_sheet('Sheet 1')

            # Define headers for the Excel file
            headers = ['StudentID', 'StudentName', 'Status', 'Date', 'EntryTime']
            for col_num, header in enumerate(headers):
                sheet1.write(0, col_num, header)

            # Write data to Excel sheet
            for row_num, row in enumerate(result, start=1):
                sheet1.write(row_num, 0, row[0])  # StudentID
                sheet1.write(row_num, 1, row[1])  # StudentName
                sheet1.write(row_num, 2, row[2])  # Status
                sheet1.write(row_num, 3, str(row[3]) if row[3] else "NA")  # Date
                sheet1.write(row_num, 4, str(row[4]) if row[4] else "NA")  # EntryTime

            # Save the report with today's date
            report_name = f"attendance_report_{date}.xls"
            wb.save(report_name)

            return render(request, 'admindashboard.html', context={"mymessage": "Report Generated", "Flag": "True"})
        else:
            return render(request, 'admindashboard.html', context={"mymessage": "No data available for the report.", "Flag": "True"})

    return render(request, 'admindashboard.html')


def attendancehistory(request):
    if request.method == "POST":
        roll_number = request.POST.get("rollNumber")
        start_date = request.POST.get("startDate")
        end_date = request.POST.get("endDate")

        # Ensure the dates are formatted correctly
        if not (roll_number and start_date and end_date):
            return render(request, 'attendancehistory.html', context={"mymessage": "Please provide all required fields.", "Flag": "True"})

        cursor.execute("""
            SELECT * FROM Attendance
            WHERE student_id = %s AND date BETWEEN %s AND %s
        """, (roll_number, start_date, end_date))
        result = cursor.fetchall()

        if result:
            # Create a new Excel workbook and sheet
            wb = Workbook()
            sheet1 = wb.add_sheet('Sheet 1')

            # Define headers for the Excel file
            headers = ['StudentID', 'StudentName', 'Status', 'Date', 'EntryTime']
            for col_num, header in enumerate(headers):
                sheet1.write(0, col_num, header)

            # Write data to Excel sheet
            for row_num, row in enumerate(result, start=1):
                sheet1.write(row_num, 0, row[0])  # StudentID
                sheet1.write(row_num, 1, row[1])  # StudentName
                sheet1.write(row_num, 2, row[2])  # Status
                sheet1.write(row_num, 3, str(row[3]) if row[3] else "NA")  # Date
                sheet1.write(row_num, 4, str(row[4]) if row[4] else "NA")  # EntryTime

            # Save the report with the roll number and date range
            report_name = f"{roll_number}_{start_date}_to_{end_date}_attendance_report.xls"
            wb.save(report_name)

            return render(request, 'attendancehistory.html', context={"mymessage": "Report Generated", "Flag": "True"})
        else:
            return render(request, 'attendancehistory.html', context={"mymessage": "No data found for the provided input.", "Flag": "True"})

    return render(request, 'attendancehistory.html')

def student_details(request):
    # connection = get_connection()
    students = []
    student_data = None

    if connection:
        cursor = connection.cursor(dictionary=True)

        # Fetch all student IDs and names from 'Names' table for the dropdown
        cursor.execute("SELECT id, name FROM Names")
        students = cursor.fetchall()

        # If the form is submitted
        if request.method == "POST":
            roll_number = request.POST.get("roll_number")

            if 'update_student' in request.POST:
                # Handle the update request
                new_name = request.POST.get("student_name")
                
                # Update the student's name in 'Names' table
                cursor.execute("""
                    UPDATE Names SET name = %s WHERE id = %s
                """, (new_name, roll_number))
                
                # Update the student's name in 'Attendance' table
                cursor.execute("""
                    UPDATE Attendance SET student_name = %s WHERE student_id = %s
                """, (new_name, roll_number))
                
                connection.commit()

                return redirect('admindashboard')

            # Fetch the student details based on roll number
            cursor.execute("SELECT id, name FROM Names WHERE id = %s", (roll_number,))
            student_data = cursor.fetchone()

        # connection.close()
    else:
        print("Connection error")

    return render(request, 'student_details.html', {
        'students': students,
        'student_data': student_data
    })