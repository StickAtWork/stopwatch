import os
import sqlite3
import datetime
from uuid import uuid4
from flask import Flask, request, session, g, \
    redirect, url_for, abort, render_template, \
    flash, Response
    
from mailer import email_invoice

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update({
    "DATABASE": os.path.join(app.root_path, 'stopwatch.db'),
    "SECRET_KEY": 'dev key',
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
    
def get_project_items(project_id):
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
    db = get_db()
    cur = db.execute("""
        SELECT  action_item.name,
                time_record.phase_id,
                strftime('%Y-%m-%d', time_record.start) AS date,
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
                a.date,
                a.time_total,
                (item_rate.fee_per_hour / 60.0 )* a.time_total AS money_total
        FROM    item_rate, 
                (SELECT action_item.name,
                        action_item.rate_id,
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
    # maybe i turn this into a query, someday.
    # someday...
    grand_totals = {
        'time': sum(x['time_total'] for x in invoice),
        'money': sum(y['money_total'] for y in invoice)
    }
    return render_template("invoice.html",
                            office=office,
                            invoice=invoice,
                            grand_totals=grand_totals)
    
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
    # early out for these links because everyone should access these
    if request.endpoint in ('login', 'logout', 'static'):
        return
    do_login = True
    session_id = session.get('session_id')
    if session_id is not None:
        db = get_db()
        cur = db.execute("""
            SELECT  * 
            FROM    online_users
            WHERE   session_id = ?
            """, [session_id])
        match = cur.fetchall()
        if match:
            do_login = False
    #if do_login and not basic_access:
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
    if request.method == 'POST':
        db = get_db()
        result = db.execute("""
            SELECT  id, 
                    name, 
                    password
            FROM    user
            WHERE   name = ?
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
    print "{} after logout".format(session)
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
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    types = db.execute("SELECT * FROM item_type").fetchall()
    action_items = get_project_items(user['viewing_project_id'])
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
        INSERT INTO project (id, 
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
    action_items = get_project_items(data['project_id'])
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    types = db.execute("SELECT * FROM item_type").fetchall()
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
            SET     name=:name,
                    project_id=:project_id,
                    rate_id=:rate,
                    type_id=:type
            WHERE 
                id=:id
            """, data)
    db.commit()
    action_items = get_project_items(project_id)
    return render_template("action_items.html", 
                            action_items=action_items)

@app.route('/my_projects/delete_action_item', methods=['POST'])
def delete_action_item():
    db = get_db()
    db.execute("""
        DELETE FROM 
            action_item
        WHERE 
            id = :item_id 
        """, request.form)
    db.commit()
    action_items = get_project_items(get_online_user()['viewing_project_id'])
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
        action_items = get_project_items(project_id)
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
    print user_email
    email_invoice(invoice, user_email)
    return """
            <div style="background-color:rgb(140, 140, 140)">
                <h1>Sent invoice</h1>
            </div>
            """

#
#   Admin page
#


@app.route('/admin', methods=['GET'])
def admin():
    db = get_db()
    rates = db.execute("SELECT * FROM item_rate").fetchall()
    types = db.execute("SELECT * FROM item_type").fetchall()
    return render_template('admin.html', 
                            types=types, 
                            rates=rates)
    
@app.route('/admin/edit_rate', methods=['POST'])
def edit_rate():
    data = {k: v for k, v in request.form.iteritems()}
    # setting values so the query works properly - 'rate-id' needs
    # to be renamed and maybe some default values should be set
    data['description'] = data.pop('description') or 'Default Title'
    data['fee_per_hour'] = data.pop('fee_per_hour') or '0'
    data['id'] = data.pop('rate-id')
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
    
@app.route('/admin/edit_type', methods=['POST'])
def edit_type():
    db = get_db()
    data = {k: v for k, v in request.form.iteritems()}
    data['id'] = data.pop('type-id')
    data['description'] = data.pop('description') or 'Default Title'
    print data
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
    

#
#   Profile page
#
    
@app.route('/profile')
def profile():
    db = get_db()
    user = db.execute("""
            SELECT  *
            FROM    user
            WHERE   id = :user_id
        """, dict(get_online_user())).fetchone()
    return render_template('profile.html', 
                            user=user)
    
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', debug=True)