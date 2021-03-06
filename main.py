import os
import sqlite3
import datetime
from uuid import uuid4
from flask import Flask, request, session, g, \
    redirect, url_for, abort, render_template, \
    flash, Response
    
from mailer import email_invoice, email_new_password
from pw_utils import random_password

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update({
    "DATABASE": os.path.join(app.root_path, 'stopwatch.db'),
    "SECRET_KEY": os.urandom(24),
    "USERNAME": 'admin',
    "PASSWORD": 'default'
})

#
#   Database connection functions
#

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv
    
def get_db():
    """Used at the start of new queries"""
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db
    
def init_db():
    """Creates a new db if none exists, otherwise
    just inits current db
    """
    db = get_db()
    with app.open_resource('db.sql', mode='r') as f:
        try:
            db.cursor().executescript(f.read())
        except sqlite3.OperationalError:
            pass
    db.commit()

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
        
#
#   functions to call directly from templates
#

    
@app.context_processor
def my_utility_processor():
    def get_statuses():
        """Currently only needed within details.html,
        returns all possible project statuses.
        """
        db = get_db()
        cur = db.execute("""
            SELECT  *
            FROM    project_status
        """)
    
        return cur.fetchall()
    
    return {"get_statuses": get_statuses}

#
#   Common functions
#
        
def get_online_user():
    """Gets the user that matches the session id."""
    db = get_db()
    cur = db.execute("""
        SELECT  * 
        FROM    online_users 
        WHERE   session_id = ?
        """, [session.get('session_id')])
    return cur.fetchone()
    
def get_urls_for_user(user):
    """Returns list of SQL results for the user's
    allowed urls.
    """
    db = get_db()
    cur = db.execute("""
        SELECT  url
        FROM    permission
        WHERE   id in (
                    SELECT  permission_id
                    FROM    usergroup_permission_tie
                    WHERE   usergroup_id = (
                                SELECT  usergroup_id
                                FROM    user
                                WHERE   id = ?
                            )
                )
        """, [user['user_id']])
    return cur.fetchall()
    
def get_projects_for_user(user):
    db = get_db()
    cur = db.execute("""
        SELECT  description,
                id,
                (SELECT sum(strftime('%s', stop) - strftime('%s', start)) / 60.0 
                FROM    time_record 
                WHERE   project_id = project.id) AS project_total
        FROM    project 
        WHERE   user_id = ? 
                AND status_id != 1
        """, [user['user_id']])
    return cur.fetchall()
    
def get_open_project_items(project_id):
    """Returns all project items that are not archived.
    """
    db = get_db()
    cur = db.execute("""
        SELECT  action_item.id,
                action_item.name, 
                item_type.description AS type,
                item_rate.description,
                item_rate.fee_per_hour
        FROM    action_item, 
                item_type, 
                item_rate
        WHERE   action_item.type_id = item_type.id 
                AND action_item.rate_id = item_rate.id 
                AND action_item.project_id = ?
                AND action_item.archived != 1
        """, [project_id])
    return cur.fetchall()
    
def get_project_phases(project_id):
    db = get_db()
    cur = db.execute("""
        SELECT  id,
                project_id,
                number, 
                (SELECT sum(strftime('%s', stop) - strftime('%s', start)) / 60.0 
                FROM    time_record 
                WHERE   phase_id = phase.id) AS phase_total
        FROM    phase
        WHERE   project_id = ?
        ORDER BY    number DESC;
        """, [project_id])
    
    return cur.fetchall()
    
def get_time_records_for_phases(phases):
    """Retrieves the time records for all phases.
    
    The database saves time_record.start and time_record.stop without accounting
    for localization. Thus when we VIEW the timestamps, in order for them to
    make sense, they need to be converted to locatime.
    
    This is *particularly* important for times when timestamps are manually
    adjusted!! The server should RETURN localized timestamps but should be GIVEN
    UTC timestamps. 
    
    Some parts of the software do not need to account for this,
    like toggling timing on/off, or just calculating the difference.
    
    """
    db = get_db()
    cur = db.execute("""
        SELECT  time_record.id,
                action_item.name,
                time_record.phase_id,
                strftime('%Y-%m-%d', datetime(time_record.start, 'localtime')) AS date,
                datetime(time_record.start, 'localtime') AS start,
                datetime(time_record.stop, 'localtime') AS stop,
                (strftime('%s', time_record.stop) - strftime('%s', time_record.start)) / 60.0 AS total
        FROM    action_item,
                time_record
        WHERE   action_item.id = time_record.action_item_id 
                AND time_record.phase_id in ({})
        """.format(','.join(str(p['id']) for p in phases)))
    
    return cur.fetchall()
    
def get_bill_for_phase(phase_id): 
    """Returns an HTML table with an itemized series of timed sessions. 
    
    Should include per line item: 
        name
        date
        total minutes spent
        sub-total (minutes spent * fee per hour)
        
    Also should include a grand total for minutes spent and total fee.
    
    As of this writing this is not a standalone estimate for any goods or
    services rendered and still needs to go to accounting as it does not
    include any of their fees or taxes or anything ancillary to the actual
    timed action item.
    """
    
    db = get_db()
    invoice = db.execute("""
        SELECT  a.name,
                a.phase_id,
                a.type,
                a.date,
                a.time_total,
                (item_rate.fee_per_hour / 60.0 )* a.time_total AS money_total
        FROM    item_rate, 
                (SELECT action_item.name,
                        action_item.rate_id,
                        (SELECT description
                        FROM    item_type
                        WHERE   item_type.id = action_item.type_id) AS type,
                        time_record.phase_id,
                        strftime('%Y-%m-%d', time_record.start) AS date,
                sum(strftime('%s', stop) - strftime('%s', start))/ 60.0 AS time_total
                FROM    action_item,
                        time_record
                WHERE   action_item.id = time_record.action_item_id
                        AND time_record.phase_id = ?
                GROUP BY    action_item.id
            ) AS a
        WHERE   a.rate_id = item_rate.id
        """, [phase_id]).fetchall()
    office = db.execute("""
        SELECT  office_serial AS serial,
                tt_number
        FROM    project
        WHERE   project.id = (
                    SELECT  project_id
                    FROM    phase
                    WHERE   phase.id = ?
                )
        """, [phase_id]).fetchone()
    # this seems like it should be rolled into a query
    # but this will do for now
    grand_totals = {
        'time': sum(x['time_total'] for x in invoice),
        'money': sum(y['money_total'] for y in invoice)
    }
    return render_template("invoice.html",
                            office=office,
                            invoice=invoice,
                            grand_totals=grand_totals)
                            
def get_open_rates():
    db = get_db()
    return db.execute("""
        SELECT  * 
        FROM    item_rate
        WHERE   archived != 1    
        """).fetchall()
    
def get_open_types():
    db = get_db()
    return db.execute("""
        SELECT  * 
        FROM    item_type
        WHERE   archived != 1    
        """).fetchall()
    
def start_timing(item_id, phase_id):
    db = get_db()
    user = get_online_user()
    new_time = db.execute("""
        INSERT INTO time_record (id, 
                                 action_item_id, 
                                 project_id, 
                                 phase_id, 
                                 start, 
                                 stop)
        VALUES      (null, 
                    ?, 
                    ?, 
                    ?, 
                    datetime('now'), 
                    null)
        """, [item_id, user['viewing_project_id'], phase_id])
    db.execute("""
        UPDATE  online_users 
        SET     time_record_id = ?
        WHERE   user_id = ?
        """, [new_time.lastrowid, user['user_id']])
    db.commit()
    
def stop_timing():
    """Stops timing the current project, and sets
    online_users.time_record_id to NULL.
    """
    db = get_db()
    user = get_online_user()
    db.executescript("""
        UPDATE  time_record 
        SET     stop = datetime('now')
        WHERE   id = {time_record_id};
        
        UPDATE  online_users 
        SET     time_record_id=null
        WHERE   user_id = {user_id}
        """.format(**user))
    db.commit()
    
def archive_record(table, id):
    """Sets the archived flag of a record to 1.
    
    This can be a generic function since the only data
    we need is the table name and the id of the record.
    
    sqlite3 doesn't let you parameterize column names, so
    sadly we have to use str.format() to get the right
    query. This should not be unsafe since the table name 
    will only ever be passed from the function calling it
    and won't come from forms submitted from the browser.
    """
    db = get_db()
    db.execute("""
        UPDATE  {}
        SET     archived = 1
        WHERE   id = {}
        """.format(table, id))
    db.commit()
        
def retrieve_record(table, id):
    """Sets the archived flag of a record to 0.
    
    This can be a generic function since the only data
    we need is the table name and the id of the record.
    
    sqlite3 doesn't let you parameterize column names, so
    sadly we have to use str.format() to get the right
    query. This should not be unsafe since the table name 
    will only ever be passed from the function calling it
    and won't come from forms submitted from the browser.
    """
    db = get_db()
    db.execute("""
        UPDATE  {}
        SET     archived = 0
        WHERE   id = {}
        """.format(table, id))
    db.commit()
    
def get_user_list():
    db = get_db()
    return db.execute("""
        SELECT  user.id,
                user.name,
                user.email, 
                usergroup.name AS usergroup,
                user.archived
        FROM    user,
                usergroup
        WHERE   user.usergroup_id = usergroup.id
        """).fetchall()
    
#
#   Routing functions
#

#   #
#   #   login/logout
#   #
        
@app.before_request
def check_user():
    """Makes sure the request is good and the user should be able
    to access this site.
    """
    # early returns for these links.
    # everyone should access these
    if request.endpoint in ('login', 'logout', 'static'):
        return
    do_login = True
    if 'session_id' in session:
        db = get_db()
        cur = db.execute("""
            SELECT  * 
            FROM    online_users
            WHERE   session_id = ?
            """, [session['session_id']])
        match = cur.fetchall()
        if match:
            do_login = False
    if do_login:
        return redirect(url_for('login'), code=401)
    # confirm privilege to access url provided
    user = get_online_user()
    if user:
        if 'navi' not in session:
            session['navi'] = [url[0][1:] for url in get_urls_for_user(user)]
        stop_access = True
        for url in session['navi']:
            if url in request.full_path:
                stop_access = False
        if stop_access:
            return Response("Bollocks, can't go here", 500)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # i think this is the best way to take care
    # of lingering permissions from old sessions?
    # if there is no match, and do_login is still true,
    # then the session should be cleared because we wouldn't
    # care about any session data anyway.
    session.clear()
    if request.method == 'POST':
        db = get_db()
        result = db.execute("""
            SELECT  id, 
                    name, 
                    password
            FROM    user
            WHERE   name = ?
                    AND archived != 1
        """, [request.form['name']]).fetchall()
        if not result:
            flash("No such username")
        for user_id, name, password in result:
            if request.form['password'] == password:
                # create unique session_id to identify user
                session['session_id'] = str(uuid4())
                db.execute("""
                    INSERT INTO online_users(user_id, 
                                            session_id, 
                                            time_record_id, 
                                            viewing_project_id) 
                    VALUES (?, 
                            ?, 
                            null, 
                            null)
                    """, [user_id, session['session_id']])
                db.commit()
                flash("Welcome, {}".format(name))
                return redirect(url_for('my_projects'))
            else:
                flash("Invalid password")
    return render_template('login.html')
    
@app.route('/logout')
def logout():
    user = get_online_user()
    # there might not be anybody online
    if user:
        # if user is timing, stop it
        if user['time_record_id'] is not None:
            stop_timing()
        db = get_db()
        db.execute("""
            DELETE FROM online_users 
            WHERE       user_id = ?
            """, [user['user_id']])
        session.clear()
        db.commit()
    flash("You logged out")
    return redirect(url_for('login'), code=302)
    
#   #
#   #   end login/logout
#   #
    
@app.route('/')
def index():
    return redirect(url_for('my_projects'))
    
@app.route('/my_projects')
def my_projects():
    user = get_online_user()
    projects = get_projects_for_user(user)
    db = get_db()
    rates = get_open_rates()
    types = get_open_types()
    action_items = get_open_project_items(user['viewing_project_id'])
    details = db.execute("""
        SELECT  * 
        FROM    project 
        WHERE   id = :project_id
        """, [user['viewing_project_id']]).fetchone()
    phases = get_project_phases(user['viewing_project_id'])
    return render_template('my_projects.html', 
                            projects=projects,
                            rates=rates,
                            types=types,
                            active=user['viewing_project_id'],
                            action_items=action_items,
                            details=details,
                            phases=phases)
                            
@app.route('/my_projects/add_project', methods=['POST'])
def add_project():
    db = get_db()
    user = get_online_user()
    # a status_id of 1 means Closed, so setting it to 2 is (for now)
    # the right way to keep the project visible to the user
    db.execute("""
        INSERT INTO project     (id, 
                                tt_number, 
                                user_id, 
                                description, 
                                notes, 
                                status_id)
        VALUES             (null, 
                            null, 
                            ?, 
                            null, 
                            null, 
                            2)
        """, [user['user_id']])
    db.commit()
    projects = get_projects_for_user(user)
    return render_template('project_view.html', 
                            projects=projects)
    
@app.route('/my_projects/expanded_project', methods=['POST'])
def expanded_project():
    user = get_online_user()
    if user['time_record_id'] is not None:
        return Response("Cannot switch projects while timing.", 500)
    
    db = get_db()
    data = {
        "project_id": request.data,
        "session_id": user['session_id']
    }
    details = db.execute("""
        SELECT  * 
        FROM    project 
        WHERE   id = :project_id
        """, data).fetchone()
    db.execute("""
        UPDATE  online_users
        SET     viewing_project_id = :project_id
        WHERE   session_id = :session_id
        """, data)
    db.commit()
    action_items = get_open_project_items(data['project_id'])
    rates = get_open_rates()
    types = get_open_types()
    phases = get_project_phases(data['project_id'])
    time_records = get_time_records_for_phases(phases)
    
    return render_template('expanded_project.html',
                            details=details,
                            action_items=action_items,
                            rates=rates,
                            types=types,
                            phases=phases,
                            time_records=time_records)
    
@app.route('/my_projects/add_action_item', methods=['POST'])
def add_action_item():
    data = {k: v for k, v in request.form.iteritems()}
    if not data['name']:
        return Response("Please name the new item before submitting.", 500)
    # renaming the key in this way because for whatever reason
    # we have to send the key from the webpage as "item-id" and
    # sqlite3 hates that because it's not the right name, so wtfever
    data['id'] = data.pop('item-id')
    db = get_db()
    project_id = get_online_user()['viewing_project_id']
    if project_id is None:
        return Response("Please select a project before adding an action item.", 500)
    data['project_id'] = u'{}'.format(project_id)
    # use -1 as a signal that the new item has no id. the app will manually set
    # new projects to -1 from the item editor
    if data['id'] == '-1':
        db.execute("""
            INSERT INTO action_item (id, 
                                    name, 
                                    project_id, 
                                    rate_id, 
                                    type_id)
            VALUES (null, 
                    :name, 
                    :project_id, 
                    :rate, 
                    :type)
            """, data)
    else:
        db.execute("""
            UPDATE  action_item
            SET     name = :name,
                    project_id = :project_id,
                    rate_id = :rate,
                    type_id = :type
            WHERE 
                id = :id
            """, data)
    db.commit()
    action_items = get_open_project_items(project_id)
    return render_template("action_items.html", 
                            action_items=action_items)

@app.route('/my_projects/delete_action_item', methods=['POST'])
def delete_action_item():
    """Archives the action_item.
    """
    archive_record("action_item", request.form['item_id'])
    action_items = get_open_project_items(get_online_user()['viewing_project_id'])
    return render_template("action_items.html", 
                            action_items=action_items)
    
@app.route('/my_projects/time_action_item', methods=['POST'])
def time_action_item():
    """Start/stop toggle for timing.
    
    Checks the db to see if there's a time_record_id, which means
    the user is timing. If so, calls stop_timing(). Else, calls start_timing().
    
    Returns 'currently_timing.html'.
    """
    item_to_time = request.form['item_id']
    db = get_db()
    user = get_online_user()
    project_id = user['viewing_project_id']
    if user['time_record_id'] is not None:
        stop_timing()
        action_items = get_open_project_items(project_id)
        return render_template("action_items.html", 
                                action_items=action_items)
    else:
        latest_phase = db.execute("""
                SELECT  max(id)
                FROM    phase
                WHERE   project_id = ?
                """, [project_id]).fetchone()[0]
        if latest_phase is None:
            latest_phase = db.execute("""
                INSERT INTO phase (id, 
                                   project_id, 
                                   number)
                VALUES  (null, 
                        ?, 
                        1)
                """, [project_id]).lastrowid
            db.commit()
        start_timing(item_to_time, latest_phase)
        db.commit()
        
        timed_item = db.execute("""
            SELECT  name, 
                    id 
            FROM    action_item
            WHERE   id = ?
            """, [item_to_time]).fetchone()
        
        return render_template("currently_timing.html", 
                                item=timed_item)
                                
@app.route('/my_projects/get_phases')
def get_phases():
    phases = get_project_phases(get_online_user()['viewing_project_id'])
    time_records = get_time_records_for_phases(phases)
    return render_template("phases.html",
                            phases=phases,
                            time_records=time_records)
        
@app.route('/my_projects/add_phase', methods=['POST'])
def add_phase():
    """Creates a new phase for the current project.
    
    Checks to make sure there's an associated project; if not it returns
    an error.
    
    Increments the new phase or sets it at 1 if there were no previous phases.
    """
    db = get_db()
    user = get_online_user()
    # no project associated? no need to create phase
    if user['viewing_project_id'] is None:
        return Response("Please select a project before adding a phase.", 500)
    # gets most recent phase number so it can be incremented; 
    # if no phase number found, sets to 1.
    last_phase = db.execute("""
        SELECT  max(number)
        FROM    phase
        WHERE   phase.project_id = ?
        """, [user['viewing_project_id']]).fetchone()[0]
    if last_phase is not None:
        next_phase = last_phase + 1
    else:
        next_phase = 1
    db.execute("""
        INSERT INTO phase (id, 
                           project_id, 
                           number)
        VALUES  (null, 
                ?, 
                ?)
        """, [user['viewing_project_id'], next_phase])
    db.commit()
    
    phases = get_project_phases(user['viewing_project_id'])
    time_records = get_time_records_for_phases(phases)
    
    return render_template("phases.html", 
                            phases=phases,
                            time_records=time_records)
                            
@app.route('/my_projects/update_details', methods=['POST'])
def update_details():
    data = {k: v for k, v in request.form.iteritems()}
    # set tt_num to None if not int
    try:
        int(data['tt_number'])
    except ValueError:
        data['tt_number'] = None
    user = get_online_user()
    data['project_id'] = user['viewing_project_id']
    db = get_db()    
    db.execute("""
        UPDATE  project
        SET     tt_number = :tt_number,
                office_serial = :office_serial,
                description = :description,
                notes = :notes,
                status_id = :status
        WHERE   id = :project_id
        """, data)
    db.commit()
    projects = get_projects_for_user(user)
    return render_template("project_view.html", 
                            projects=projects,
                            active=user['viewing_project_id'])
                            
@app.route('/my_projects/preview_invoice', methods=['POST'])
def preview_invoice():
    return get_bill_for_phase(request.data)


@app.route('/my_projects/send_invoice', methods=['POST'])    
def send_invoice():
    invoice = get_bill_for_phase(request.data)
    db = get_db()
    user_email = db.execute("""
            SELECT  email
            FROM    user
            WHERE   id = ?
        """, [get_online_user()['user_id']]).fetchone()[0]
    email_invoice(user_email, invoice)
    return """
            <div style="background-color:rgb(140, 140, 140)">
                <h1>Sent invoice</h1>
            </div>
            """

#   #
#   #   Admin page
#   #


@app.route('/admin', methods=['GET'])
def admin():
    db = get_db()
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    types = db.execute("SELECT * FROM item_type").fetchall()
    users = get_user_list()
    groups = db.execute("SELECT * FROM usergroup").fetchall()
    return render_template('admin.html', 
                            types=types, 
                            rates=rates,
                            users=users,
                            groups=groups)
    
@app.route('/admin/edit_rate', methods=['POST'])
def edit_rate():
    data = {k: v for k, v in request.form.iteritems()}
    # setting values so the query works properly - 'rate-id' needs
    # to be renamed and maybe some default values should be set
    data['description'] = data.pop('description') or None
    data['fee_per_hour'] = data.pop('fee_per_hour') or 0
    data['id'] = data.pop('rate-id', None)
    db = get_db()
    if data['id'] == '-1':
        db.execute("""
            INSERT INTO item_rate (id, 
                                   description, 
                                   fee_per_hour)
            VALUES  (null, 
                    :description, 
                    :fee_per_hour)
        """, data)
    else:
        db.execute("""
            UPDATE  item_rate
            SET     description = :description,
                    fee_per_hour = :fee_per_hour
            WHERE   id = :id
        
        """, data)
        
    db.commit()
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    return render_template('rate_editor.html', 
                            rates=rates)
                            
@app.route('/admin/archive_rate', methods=['POST'])
def archive_rate():
    archive_record('item_rate', request.form['rate-id'])
    db = get_db()
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    return render_template('rate_editor.html',
                            rates=rates)
                            
@app.route('/admin/retrieve_rate', methods=['POST'])
def retrieve_rate():
    retrieve_record('item_rate', request.form['rate-id'])
    db = get_db()
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    return render_template('rate_editor.html',
                            rates=rates)
    
    
@app.route('/admin/edit_type', methods=['POST'])
def edit_type():
    db = get_db()
    data = {k: v for k, v in request.form.iteritems()}
    data['id'] = data.pop('type-id', None)
    data['description'] = data.pop('description') or None
    if data['id'] == '-1':
        db.execute("""
            INSERT INTO item_type (id, 
                                   description)
            VALUES  (null, 
                    :description)
        """, data)
    else:
        db.execute("""
            UPDATE  item_type
            SET     description = :description
            WHERE   id = :id
        """, data)
    db.commit()
    types = db.execute("SELECT * FROM item_type").fetchall()
    return render_template('type_editor.html', 
                            types=types)
                            
@app.route('/admin/archive_type', methods=['POST'])
def archive_type():
    archive_record('item_type', request.form['type-id'])
    db = get_db()
    types = db.execute("SELECT * FROM item_type").fetchall()
    return render_template('type_editor.html',
                            types=types)

@app.route('/admin/retrieve_type', methods=['POST'])
def retrieve_type():
    retrieve_record('item_type', request.form['type-id'])
    db = get_db()
    types = db.execute("SELECT * FROM item_type").fetchall()
    return render_template('type_editor.html',
                            types=types)
                            
@app.route('/admin/edit_user', methods=['POST'])
def edit_user():
    data = {k: v for k, v in request.form.iteritems()}
    data['id'] = data.pop('user-id')
    data['usergroup_id'] = data.pop('usergroup')
    db = get_db()
    if data['id'] == '-1':
        # EW FUTURE PROOFING
        # actually i just think this is a really primitive
        # way to handle this issue, but it will work for now.
        #
        # it MIGHT be ideal to let the admin user just set the password
        # in the future but for now it's desired to keep passwords as secret
        # as they can be
        if 'password' not in data:
            data['password'] = random_password()
        db.execute("""
            INSERT INTO user   (id,
                                name,
                                email,
                                password,
                                usergroup_id)
            VALUES  (null,
                    :name,
                    :email,
                    :password,
                    :usergroup_id)
        """, data)
        email_new_password(data['email'], data['name'], data['password'])
    else:
        db.execute("""
            UPDATE  user
            SET     name = :name,
                    email = :email,
                    usergroup_id = :usergroup_id
            WHERE   id = :id
        """, data)
    db.commit()
    users = get_user_list()
    groups = db.execute("""SELECT * from usergroup""")
    return render_template("user_editor.html",
                            users=users,
                            groups=groups)   

                         
@app.route('/admin/archive_user', methods=['POST'])
def archive_user():
    archive_record("user", request.form['user-id'])
    db = get_db()
    users = get_user_list()
    groups = db.execute("""SELECT * from usergroup""")
    return render_template("user_editor.html",
                            users=users,
                            groups=groups)


@app.route('/admin/retrieve_user', methods=['POST'])
def retrieve_user():
    retrieve_record("user", request.form['user-id'])
    db = get_db()
    users = get_user_list()
    groups = db.execute("""SELECT * from usergroup""")
    return render_template("user_editor.html",
                            users=users,
                            groups=groups)
                            
@app.route('/admin/reset_password', methods=['POST'])
def reset_password():
    if request.form['user-id'] == '-1':
        return Response("No user selected", 500)
    data = {
        "id": request.form['user-id'],
        "password": random_password()
    }
    db = get_db()
    db.execute("""
        UPDATE  user
        SET     password = :password
        WHERE   id = :id
    """, data)
    email_new_password(request.form['email'], 
                       request.form['name'], 
                       data['password'])
    db.commit()
    users = get_user_list()
    groups = db.execute("""SELECT * from usergroup""")
    return render_template("user_editor.html",
                            users=users,
                            groups=groups)


#   #
#   #   Profile page
#   #

@app.route('/profile')
def profile():
    db = get_db()
    data = dict(get_online_user())
    user = db.execute("""
            SELECT  *
            FROM    user
            WHERE   id = :user_id
        """, data).fetchone()
    return render_template('profile.html', 
                            user=user)
                            
@app.route('/profile/edit_profile', methods=['POST'])
def edit_profile():
    """Updates the user profile with the provided information.
    
    Does NOT return a template because there should be no
    reason to return data that is already represented in the
    current view.
    """
    data = {}
    for k, v in request.form.iteritems():
        if not v:
            return Response("Required: {}".format(k), 500)
        else:
            data[k] = v
    data['id'] = get_online_user()['user_id']
    db = get_db()
    db.execute("""
        UPDATE  user
        SET     name = :name,
                email = :email
        WHERE   id = :id
    """, data)
    db.commit()
    return Response('Information updated.', 500)
    
@app.route('/profile/edit_password', methods=['POST'])
def edit_password():
    """Updates the user password.
    
    Does NOT return a template because there should be no
    reason to return data that is already represented in the
    current view.
    """
    data = {}
    for k, v in request.form.iteritems():
        if not v:
            # don't want blanks for this kind of
            # data entry, nope nope
            return Response("Required: {} password".format(k), 500)
        else:
            data[k] = v
    db = get_db()
    # confirms that the password is correct
    # AND is for the online_user.
    # unlike other record ids this one isn't
    # stored on the page so I'm getting it out
    # of the db
    confirm = {
        "id": get_online_user()['user_id'],
        "password": data['old']
    }
    user = db.execute("""
        SELECT  *
        FROM    user
        WHERE   id = :id
                AND password = :password
        """, confirm).fetchone()
    if user:
        id_pw = {
            "id": confirm['id'],
            "password": data['new']
        }
        db.execute("""
            UPDATE  user
            SET     password = :password
            WHERE   id = :id
        """, id_pw)
        email_new_password(user['email'], user['name'], id_pw['password'])
        db.commit()
    else:
        return Response('No match for that password', 500)
    return Response('Password changed, email sent to {}'.format(user['email']), 500)
    
                            
#   #
#   #   Adjustments page
#   #
    
@app.route('/adjustments')
def adjustments():
    return render_template('adjustments.html')
    
@app.route('/adjustments/search_by_project', methods=['POST'])
def search_by_project():
    phases = get_project_phases(request.form['project-id'])
    time_records = get_time_records_for_phases(phases)
    return render_template("adjustment_search_results.html",
                            phases=phases,
                            time_records=time_records)
                            
@app.route('/adjustments/edit_time_records', methods=['POST'])
def edit_time_records():
    """Allows user to manually modify time_records.
    
    The timestamps are saved in the database as UTC timestamps during the
    start/stop timing process, but this view needs to convert them to localtime
    in order for manual edits to make any sense. For that reason they are 
    converted back to UTC before they are saved again.
    
    """
    data = {}
    for k, v in request.form.iteritems():
        # verify that the timestamps entered are legitimate
        # datetime values. if they are, add them to the data dict.
        # if they are not, send response to the user.
        if k in ('start', 'stop'):
            try:
                data[k] = datetime.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return Response('\n'.join([
                    "'{}' was not a valid datetime.".format(k.capitalize()),
                    "Valid datetimes are yyyy-mm-dd 24:00:00."
                    ]), 500)
            #else:
            #    data[k] = v
    data['id'] = request.form['record-id']
    data['phase_id'] = request.form['phase']
    db = get_db()
    # Notice the timestamp converts back to UTC here
    db.execute("""
        UPDATE  time_record
        SET     start = datetime(:start, 'utc'),
                stop = datetime(:stop, 'utc'),
                phase_id = :phase_id
        WHERE   id = :id
    """, data)
    db.commit()
    phases = get_project_phases(request.form['project-id'])
    time_records = get_time_records_for_phases(phases)
    return render_template("adjustment_search_results.html",
                            phases=phases,
                            time_records=time_records,
                            last_record_altered=int(data['id']))
                            
#   #
#   #   Reports page
#   #

#####
#
#   I must now pay for my sins of rejecting OOP
#
#####

ALL_REPORTS = {
        "Total Time Per Item Type": """
            SELECT  sum(
                        strftime('%s', time_record.stop) 
                        - strftime('%s', time_record.start)
                    ) 
                    / 60.0 
                    AS total, 
                    item_type.description 
                    AS description
            FROM    time_record, 
                    action_item, 
                    item_type 
            WHERE   action_item.id = time_record.action_item_id 
            AND     action_item.type_id = item_type.id 
            AND     time_record.start 
                BETWEEN     datetime(:start, 'utc')
                AND         datetime(:end, 'utc')
            GROUP BY    action_item.type_id
            """
    }
                            
@app.route('/reports')
def reports():
    """For now this returns the results of one kind of query.
    
    That'll change.
    """
    #db = get_db()
    #results = db.execute("""
    #    SELECT  sum(strftime('%s', time_record.stop) - strftime('%s', time_record.start)) / 60.0 AS total, 
    #            item_type.description AS description
    #    FROM    time_record, 
    #            action_item, 
    #            item_type 
    #    WHERE   action_item.id = time_record.action_item_id 
    #    AND     action_item.type_id = item_type.id 
    #    GROUP BY    action_item.type_id
    #    """)
    return render_template('reports.html')
                            
@app.route('/reports/run_report', methods=['POST'])
def run_report():
    data = {}
    for k, v in request.form.iteritems():
        if k in ('start', 'end'):
            try:
                data[k] = datetime.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return Response('\n'.join([
                    "'{}' was not a valid datetime.".format(k.capitalize()),
                    "Valid datetimes are yyyy-mm-dd 24:00:00."
                    ]), 500)
    db = get_db()
    #results = db.execute("""
    #    SELECT  sum(strftime('%s', time_record.stop) - strftime('%s', time_record.start)) / 60.0 AS total, 
    #            item_type.description AS description
    #    FROM    time_record, 
    #            action_item, 
    #            item_type 
    #    WHERE   action_item.id = time_record.action_item_id 
    #    AND     action_item.type_id = item_type.id 
    #    AND     time_record.start 
    #        BETWEEN     datetime(:start, 'utc')
    #        AND         datetime(:end, 'utc')
    #    GROUP BY    action_item.type_id
    #    """, data)
    report = ALL_REPORTS['Total Time Per Item Type']
    results = db.execute(report, data)
    return render_template('report_results.html',
                            results=results)
        
    

#
#   makes it go!
#
    
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', debug=True)