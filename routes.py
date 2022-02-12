from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import LoginForm
from flaskext.mysql import MySQL
from datetime import date, datetime
from time import sleep
from collections import OrderedDict
import dbConfig
import pymysql
import json


@app.route('/')
@app.route('/index')
def index():
    mysql = MySQL()
    app.config['MYSQL_DATABASE_USER'] = dbConfig.dbConfigInfo['user']
    app.config['MYSQL_DATABASE_PASSWORD'] = dbConfig.dbConfigInfo['password']
    app.config['MYSQL_DATABASE_DB'] = dbConfig.dbConfigInfo['database']
    app.config['MYSQL_DATABASE_HOST'] = dbConfig.dbConfigInfo['host']
    mysql.init_app(app)
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams")
    entries = cursor.fetchall()
    conn.close()
    return render_template('index.html', title='Home',
                           entries=entries)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(form.username.data, form.remember_me.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In',
                           form=form)


@app.route('/team_page/<team>', methods=['GET', 'POST'])
def team_page(team):
    # connect to MySQL db, get prospects for team that was clicked (see index.html)
    mysql = MySQL()
    app.config['MYSQL_DATABASE_USER'] = dbConfig.dbConfigInfo['user']
    app.config['MYSQL_DATABASE_PASSWORD'] = dbConfig.dbConfigInfo['password']
    app.config['MYSQL_DATABASE_DB'] = dbConfig.dbConfigInfo['database']
    app.config['MYSQL_DATABASE_HOST'] = dbConfig.dbConfigInfo['host']
    mysql.init_app(app)
    conn = mysql.connect()
    cursor = conn.cursor()
    sql = "SELECT * FROM prospects WHERE team =%s"
    val = team
    cursor.execute(sql, val)
    prospects_tup = cursor.fetchall()
    conn.close()
    # create empty lists for prospects or no prospect bit
    prospects = []
    no_prospects = []
    # if prospects exist
    if len(prospects_tup) > 0:
        # data retrieved as a tuple, need to convert to list in order to append age after calculation
        prospects_list = [list(row) for row in prospects_tup]
        for prospect in prospects_list:
            # calculate age
            dob = prospect[5]
            b_mon = int(dob[0:2])
            b_day = int(dob[3:5])
            b_year = int(dob[6:10])
            today = date.today()
            age = today.year - b_year - ((today.month, today.day) < (b_mon, b_day))
            # append age to player data
            prospect.append(age)
            # append player data to whole list of lists
            prospects.append(prospect)
    # if no prospects exist
    else:
        no_prospects.append('True')
    return render_template('team_page.html', title=team,
                           team=team,
                           prospects=prospects,
                           no_prospects=no_prospects)


@app.route('/player_page/<player>', methods=['GET', 'POST'])
def player_page(player):
    # connect to MySQL db, get game log data for player that was clicked
    mysql = MySQL()
    app.config['MYSQL_DATABASE_USER'] = dbConfig.dbConfigInfo['user']
    app.config['MYSQL_DATABASE_PASSWORD'] = dbConfig.dbConfigInfo['password']
    app.config['MYSQL_DATABASE_DB'] = dbConfig.dbConfigInfo['database']
    app.config['MYSQL_DATABASE_HOST'] = dbConfig.dbConfigInfo['host']
    mysql.init_app(app)
    conn = mysql.connect()
    cursor = conn.cursor()

    # GET GAME LOG DATA
    #   format player name for sql query
    #       get rid of spaces between names
    sql_player_0 = player.replace(" ", "")
    #   get rid of any hyphens in name
    sql_player = sql_player_0.replace("-", "")
    #   assemble sql query
    #       can only select common rows between all leagues:
    #           --> Date, Season, Team, League, Opponent, Goals, Assists, Total, PIM, SOG, PlusMinus
    #           --> condition for SOG to note equal 'Exhibition' is due to exhibition/DNPs for NCAA league
    sql = "SELECT Date, Season, Team, League, Opponent, Goals, Assists, Total, PIM, SOG, PlusMinus " \
          "FROM " + sql_player + " WHERE SOG !=%s"
    val = 'Exhibition'
    #   create empty lists for game log data or in case player doesn't exists in database yet
    game_log_data = []
    no_game_log_data = []
    try:
    #   get game log data
        cursor.execute(sql, val)
        game_log_data = cursor.fetchall()
    #   following error is generated if player game log table does not exist:
    #   --> pymysql.err.ProgrammingError: (1146, "Table 'NHL.PlayerName' doesn't exist")
    except pymysql.err.ProgrammingError:
    #   set flag for no data to True
        no_game_log_data.append('True')

    # GET PLAYER INFORMATION
    #   sql statements for player information
    sql_player_data = "SELECT * from prospects WHERE Name=%s"
    val_player_data = player
    #   get player information
    cursor.execute(sql_player_data, val_player_data)
    player_info_tup = cursor.fetchall()
    #   set player information
    player_info = player_info_tup[0]
    #   calculate age
    dob = player_info[5]
    b_mon = int(dob[0:2])
    b_day = int(dob[3:5])
    b_year = int(dob[6:10])
    today = date.today()
    age = today.year - b_year - ((today.month, today.day) < (b_mon, b_day))

    # GET UNIQUE SEASONS
    #   create empty list for values
    unique_season = []
    #   sql statements for db query
    sql_unique_season = "SELECT DISTINCT Season FROM " + sql_player + " WHERE SOG !=%s"
    val_unique_season = "Exhibition"
    #   query database
    cursor.execute(sql_unique_season, val_unique_season)
    unique_season_tup = cursor.fetchall()
    for season in unique_season_tup:
        unique_season.append(season[0])

    # GET CUMULATIVE OF GOALS, ASSISTS, POINTS BY SEASON
    #   Create empty dictionary
    data_dict = {}
    dates_dict = {}
    for season in unique_season:
    #   Get dates for unique season
        sql_cumul_date = "SELECT Date FROM " + sql_player + " WHERE Season=%s"
        val_cumul = season
        cursor.execute(sql_cumul_date, val_cumul)
        date_data = cursor.fetchall()
    #   Get goals for unique season
        sql_cumul_goals = "SELECT Goals FROM " + sql_player + " WHERE Season=%s"
        cursor.execute(sql_cumul_goals, val_cumul)
        goals_data = cursor.fetchall()
    #   Get assists for unique season
        sql_cumul_assists = "SELECT Assists FROM " + sql_player + " WHERE Season=%s"
        cursor.execute(sql_cumul_assists, val_cumul)
        assists_data = cursor.fetchall()
    #   Get points for unique season
        sql_cumul_points = "SELECT Total FROM " + sql_player + " WHERE Season=%s"
        cursor.execute(sql_cumul_points, val_cumul)
        points_data = cursor.fetchall()
    #   Convert data into lists
        dates = []
        for date_i in date_data:
            dates.append(date_i[0].strftime("%m/%d/%Y"))
        goals = []
        for goal_i in goals_data:
            goals.append(goal_i[0])
        assists = []
        for assists_i in assists_data:
            assists.append(assists_i[0])
        points = []
        for points_i in points_data:
            points.append(points_i[0])
    #   Assemble cumulative lists
    #   Goals
        cumul_goals = []
        total_goals = 0
        for goal_j in goals:
            total_goals = total_goals + int(goal_j)
            cumul_goals.append(str(total_goals))
    #   Assists
        cumul_assists = []
        total_assists = 0
        for assists_j in assists:
            total_assists = total_assists + int(assists_j)
            cumul_assists.append(str(total_assists))
    #   Points
        cumul_points = []
        total_points = 0
        for points_j in points:
            total_points = total_points + int(points_j)
            cumul_points.append(str(total_points))
    #   Append new data to dictionary
        data_dict[season] = {'Goals': cumul_goals, 'Assists': cumul_assists, 'Points': cumul_points, 'Dates': dates}
    


    # end of database queries - close db connection
    conn.close()

    # need to format Opponent
    #   add opponent to list
    opponent_all = []
    for game in game_log_data:
        opp = game[4]
    #   get rid of "at "
        if opp[:3] == "at " or "vs ":
            opp = opp.replace("at ", "")
            opp = opp.replace("vs ", "")
    #   capitalize first letter of word in string
        opp_new = opp.title()
        opponent_all.append(opp_new)

    # render player page template
    return render_template('player_page.html', title=player,
                           player=player,
                           game_log_data=game_log_data,
                           no_game_log_data=no_game_log_data,
                           opponent_all=opponent_all,
                           player_info=player_info,
                           age=age,
                           unique_season=unique_season,
                           data_dict=data_dict)
