import datetime
import json
import sqlite3

# connect to database
connectDB = sqlite3.connect('attendance(1)[6].db')

# add cursor to excute sql query
c = connectDB.cursor()

# time formate will use foe all function
Timeformate = '%Y-%m-%d %I:%M %p'


def get_attendance(employee, date):
    """function that accepts an employee code (e.g. EMP01) and a date (e.g. 2020-04-01)

    Args:
        employee (string): code of employee
        date (string): date in string fromate

    Returns:
        [Dictionary]: and reports whether the employee has attended that day and how long.
    """
    # empty list to append the date come from database, after convert it from tuple to string
    day = []
    # excute sql query to get list of data each date come as tuple [('2020-04-01',)]
    FetchDay = c.execute("SELECT day FROM Attendance where employee=:employee", {
                         'employee': employee})
    # get all date as list of tuples
    day_as_tuple = c.fetchall()

    # iterate over list of tuple and append each date to day list
    for days in day_as_tuple:
        for ele in days:
            day.append(ele)

    # test the case to check if date in day list or not
    if date in day:
        attended = True
    else:
        attended = False

    # make report as dictionary
    report = {}
    report['attended'] = attended
    # Time duration function to compute time duration
    duration = TimeDuration(employee, date)
    report['duration'] = str(duration)[:5]
    return report


def TimeDuration(employee, date):
    """Function that calculate the working time duration for each employee 
        this function call from get_attendace() function.  
    """
    # fetch data from database ActionTime to get difference between each checkIn and checkout
    FetchDateTime = c.execute("""SELECT ActionTime
                                FROM AttendanceActions
                                JOIN Attendance A on A.Id = AttendanceActions.AttendanceId
                                WHERE employee=:employee
                                AND ActionTime LIKE (:date)""", {'employee': employee, 'date': '%' + date + '%'})
    # get all rows from database
    DateTime_as_tuple = c.fetchall()

    # empty list to store formatted datetime
    # Dt store datetime as string coming form database
    Dt = []
    # StoreDate store converted datetime into  datetime type using datetime lib
    StoreDate = []

    # append all tuple value in list coming from database to list "clean"
    for DTimes in DateTime_as_tuple:
        for ele in DTimes:
            Dt.append(ele)

    # get length of that list to use it in important process
    Dt_length = len(Dt)

    # convert all element in Dt list from string to datetime type and append it to StoreDate database
    for i in range(Dt_length):
        StoreDate.append(datetime.datetime.strptime(Dt[i], Timeformate))

    # Create action variable to use it for missing checkIn or checkout by employees
    Action = None

    # this condition know if there are missing checkIN or out by employees
    if Dt_length % 2 != 0:
        # Get last action by employee to know tha last action in the days
        FetchAction = c.execute("""select  Action
                                   from AttendanceActions
                                   join Attendance A on A.Id = AttendanceActions.AttendanceId
                                   where employee= :employee AND ActionTime like :datetime;""",
                                {'employee': employee, 'datetime': Dt[Dt_length-1]})
        # convert it to string should be string as "checkIn" or "checkOut"
        Action = c.fetchone()
        Action = ''.join(Action)

    # get last date realted to last action by employees
    year = datetime.datetime.strptime(Dt[Dt_length-1], Timeformate).year
    month = datetime.datetime.strptime(Dt[Dt_length-1], Timeformate).month
    day = datetime.datetime.strptime(Dt[Dt_length-1], Timeformate).day

    # if last action is checkIn employee miss to check out and the time closed by midnight as required
    if Action == "CheckIn":
        MidNight = datetime.datetime(year, month, day, 23, 59, 59)
        # append that day to StoreDate list to contribute to calculation
        StoreDate.append(MidNight)

    # if  last action is checkout employee forget to check in time calculate passed in previous day
    if Action == "CheckOut":
        PreviousDay = datetime.datetime(year, month, day-1, 23, 59, 59)
        StoreDate.append(PreviousDay)
        # add reverse method here to undo comming reverse that not required if that checkout case
        StoreDate.reverse()

    # reverse list to subtract last day from next day
    StoreDate.reverse()
    # make total variable to collect the number for each two datetime different
    total = datetime.datetime.now().replace(second=0, microsecond=0)

    # check out if the length of list is = 1 or not to avoid index error
    # and give j  variable the will subtracted from Dt_length in range() method in next loop
    # if Dt_length = 1 and subtract 1  from it the loop will never enter
    #  so put j= 0 if equal 1 and j = 1 otherwise
    if Dt_length == 1:
        j = 0
    else:
        j = 1

    # make variable that will use in loop to be independent from loop variable i
    n = 0
    # final step to calculate time duration for employee
    for i in range(Dt_length-j):
        value = StoreDate[n] - StoreDate[n+1]
        total += value
        n += 2
    # time correction in required formate
    duration = total-datetime.datetime.now().replace(second=0, microsecond=0)
    duration = duration + datetime.timedelta(seconds=1)
    return duration


def get_attendance_history(EmployeeCode):
    """function that accepts an employee code (e.g. EMP01)
        and returns the attendance history for that employee.

    Args:
        EmployeeCode (string): [description]

    Returns:
        [string]: the attendance history for that employee. in(JSON representation of dict)
    """
    # FetchHistory is a Variable use execute mehtod from SqLite to get data desired from database
    # the data we will work on from day, action and actiontime column
    FetchHistory = c.execute("""SELECT day, action, ActionTime
                                FROM AttendanceActions
                                JOIN Attendance A on A.Id = AttendanceActions.AttendanceId
                                WHERE employee= :employee;""", {'employee': EmployeeCode})
    # use fetchall method to get all rows from database
    HistoryAsTuple = c.fetchall()

    # some Variable will help to fromate results in the required formate
    # MajorList: the big List container that will hold all SubDictionary
    MajorList = []
    # TemporaryDict: will hold some data help in formating but changing every iteration
    # this variable will tell program when put a new day and update the existing one
    TemporaryDict = {'date': '', 'actions': []}
    # SubDict: that contain actions information
    SubDict = {}
    # the final result will hold by that variable and letter converted to json fromat
    AttendanceHistory = {}
    # iterate over the database fetches to start formating and convert to json
    for ele in HistoryAsTuple:
        # check if the day is repeated in next rows or not to take action
        # if repeated scape this step
        if TemporaryDict['date'] != ele[0]:
            # this steps contain 1. update date key in TemporaryDict as subDictionres
            TemporaryDict['date'] = ele[0]
            # initialize actions key and its value as list to add actions and time to it
            TemporaryDict['actions'] = []
            # add whole TemporaryDict to MajorList
            MajorList.append(TemporaryDict.copy())
        # update actions by actions and time  list in TemproryDict "or" create new one for new date or day
        SubDict['action'] = ele[1]
        # change time formate to UTC ISO format
        SubDict['time'] = datetime.datetime.strptime(
            ele[2], Timeformate).isoformat()
        # update TemproryDict with actions taken
        TemporaryDict['actions'].append(SubDict.copy())
        # clear that dict
        SubDict = {}
    # add key to AttendanceHistory to add Major List to it
    AttendanceHistory['days'] = MajorList
    # make json fromate useing Dumps formate and indent
    return json.dumps(AttendanceHistory, indent=2)


# testCase run the code to see the output
# case 1
print('-'*50, 'CASE1', '-'*50)
employee = 'EMP01'
date = '2020-04-01'
testCase1 = get_attendance(employee, date)
print(testCase1)
# case 2
print('-'*50, 'CASE2', '-'*50)
EmployeeCode = 'EMP01'
testCase2 = get_attendance_history(EmployeeCode)
print(testCase2)
