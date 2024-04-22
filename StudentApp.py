from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion
table = customtable

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)

output = {}
table = 'student'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('AddStudent.html')


@app.route("/about", methods=['GET', 'POST'])
def about():
    return render_template('About.html')


@app.route("/addstudent", methods=['POST'])
def AddStudent():
    student_id = request.form['student_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    gpa = request.form['gpa']
    courses = request.form['courses']
    student_image_file = request.files['student_image_file']

    insert_sql = "INSERT INTO student VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if student_image_file.filename == "":
        return "Please select a file"

    try:
        cursor.execute(insert_sql, (student_id, first_name, last_name, gpa, courses))
        db_conn.commit()
        student_name = "" + first_name + " " + last_name

        # Upload image file in S3
        student_image_file_name_in_s3 = "student-id-" + str(student_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=student_image_file_name_in_s3, Body=student_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                student_image_file_name_in_s3)

            # Save image file metadata in DynamoDB
            print("Uploading to S3 success... saving metadata in DynamoDB...")
            try:
                dynamodb_client = boto3.client('dynamodb', region_name=customregion)
                dynamodb_client.put_item(
                    TableName=customtable,
                    Item={
                        'studentid': {
                            'N': student_id
                        },
                        'image_url': {
                            'S': object_url
                        }
                    }
                )

            except Exception as e:
                return str(e)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddStudentOutput.html', name=student_name)


@app.route("/getstudent", methods=['GET', 'POST'])
def GetStudent():
    return render_template("GetStudent.html")


# @app.route("/fetchstudentdata", methods=['POST'])
# def FetchStudentData():
#     student_id = request.form['student_id']

#     output = {}
#     select_sql = "SELECT student_id, first_name, last_name, gpa, courses from student where student_id=%s"
#     cursor = db_conn.cursor()

#     try:
#         cursor.execute(select_sql, (student_id,))
#         result = cursor.fetchone()

#         output["student_id"] = result[0]
#         output["first_name"] = result[1]
#         output["last_name"] = result[2]
#         output["gpa"] = result[3]
#         output["courses"] = result[4]

#         dynamodb_client = boto3.client('dynamodb', region_name=customregion)
#         try:
#             response = dynamodb_client.get_item(
#                 TableName=customtable,
#                 Key={
#                     'studentid': {
#                         'N': str(student_id)
#                     }
#                 }
#             )
#             image_url = response['Item']['image_url']['S']

#         except Exception as e:
#             return str(e)

#     except Exception as e:
#         print(e)

#     finally:
#         cursor.close()

#     return render_template("GetStudentOutput.html", id=output["student_id"], fname=output["first_name"],
#                            lname=output["last_name"], gpa=output["gpa"], courses=output["courses"],
#                            image_url=image_url)

@app.route("/fetchstudentdata", methods=['POST'])
def FetchStudentData():
    student_id = request.form['student_id']

    output = {}
    select_sql = "SELECT student_id, first_name, last_name, gpa, courses from student where student_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (student_id,))
        result = cursor.fetchone()

        output["student_id"] = result[0]
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["gpa"] = result[3]
        output["courses"] = result[4]

        # Remove DynamoDB related code
        # Dynamically build image URL instead
        student_image_file_name_in_s3 = "student-id-" + str(student_id) + "_image_file"
        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

        image_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            student_image_file_name_in_s3
        )

    except Exception as e:
        print(e)
        return str(e)

    finally:
        cursor.close()

    return render_template("GetStudentOutput.html", id=output["student_id"], fname=output["first_name"],
                           lname=output["last_name"], gpa=output["gpa"], courses=output["courses"],
                           image_url=image_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)