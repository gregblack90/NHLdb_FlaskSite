from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import LoginForm
from flaskext.mysql import MySQL
from datetime import date
import dbConfig
import pymysql


@app.route('/')
@app.route('/index')
def index():
    mysql = MySQL()
    app.config['MYSQL_DATABASE_USER'] = 'website'
    app.config['MYSQL_DATABASE_PASSWORD'] = '123861'
    app.config['MYSQL_DATABASE_DB'] = 'NHL'
    app.config['MYSQL_DATABASE_HOST'] = '192.168.1.154'
    mysql.init_app(app)
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams")
    entries = cursor.fetchall()
    conn.close()
    return render_template('index.html', title='Home', entries=entries)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(form.username.data, form.remember_me.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


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
    return render_template('team_page.html', title=team, team=team, prospects=prospects, no_prospects=no_prospects)


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
    # get rid of spaces between names
    sql_player_0 = player.replace(" ", "")
    # get rid of any hyphens in name
    sql_player = sql_player_0.replace("-", "")
    # can only select common rows between all leagues:
    # --> Date, Season, Team, League, Opponent, Goals, Assists, Total, PIM, SOG, PlusMinus
    # --> condition for SOG to note equal 'Exhibition' is due to exhibition/DNPs for NCAA league
    sql = "SELECT Date, Season, Team, League, Opponent, Goals, Assists, Total, PIM, SOG, PlusMinus " \
          "FROM " + sql_player + " WHERE SOG !=%s"
    val = 'Exhibition'
    # create empty lists for game log data or in case player doesn't exists in database yet
    game_log_data = []
    no_game_log_data = []
    try:
        cursor.execute(sql, val)
        game_log_data = cursor.fetchall()
    # following error is generated if player game log table does not exist:
    # --> pymysql.err.ProgrammingError: (1146, "Table 'NHL.PlayerName' doesn't exist")
    except pymysql.err.ProgrammingError:
        no_game_log_data.append('True')
    conn.close()
    return render_template('player_page.html', title=player,
                           player=player, game_log_data=game_log_data, no_game_log_data=no_game_log_data)
