import datetime
import psycopg2
import requests
import sched
import time



# connecting to the database
con = psycopg2.connect(
      database="your_database_name",
      user="your_username",
      password="your_password",
      host="your_host/localhost",
      port="your_port"
    )

# creation of cursor and table
cur = con.cursor()
cur.execute('''CREATE TABLE your_table_name
     (Y_M_D CHAR(50),
      PROJECT CHAR(100),
      PROJECT_SECONDS INT NOT NULL,
      USERNAME CHAR(50),
      TASK CHAR(100),
      TASK_SECONDS INT NOT NULL);''')
con.commit()

s = sched.scheduler(time.time, time.sleep)


def parser(auto):

    """ This function automaticaly authorize in your trackingtime account
    and insert into SQL table current date, project name, how many seconds
    were spent on this project, username of person, task that he is doing,
    and how many seconds were spent on this task. Also, it repeats every
    1 hour"""

    login = 'your_login'
    password = 'your_password'
    url = 'https://app.trackingtime.co/api/v4/tasks'
    response = requests.get(url, auth=(login, password))
    for i in range(len(response.json()['data'])):
        if response.json()['data'][i]['project'] is None:
            pass
        else:
            p_date = str(datetime.datetime.now())[:-15]  # current date
            p_project = response.json()['data'][i]['project']  # the name of the project
            p_proj_time = response.json()['data'][i]['project_accumulated_time']  # seconds, spent on this project
            p_name = response.json()['data'][i]['user']['name']  # username of person, who is doing the task
            p_task = response.json()['data'][i]['name']  # the name of the task
            p_task_time = response.json()['data'][i]['accumulated_time']  # seconds, spent on this task

            cur.execute(
              "INSERT INTO your_table_name (Y_M_D,PROJECT,PROJECT_SECONDS,USERNAME,TASK,TASK_SECONDS)\
               VALUES ('%s', '%s', '%s', '%s', '%s', '%s')"\
              % (p_date, p_project, int(p_proj_time), p_name, p_task, int(p_task_time))
            )

            con.commit()
            print("Record inserted successfully")  # to know, that everything is going ok :)

    s.enter(3600, 1, parser, (auto,))


s.enter(3600, 1, parser, (s,))
s.run()
