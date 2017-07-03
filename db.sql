CREATE TABLE action_item (
    id INTEGER PRIMARY KEY,
    name TEXT,
    project_id INTEGER,
    rate_id INTEGER,
    type_id INTEGER,
    archived INTEGER DEFAULT 0
);

CREATE TABLE time_record (
    id INTEGER PRIMARY KEY, 
    action_item_id INTEGER,
    project_id INTEGER,
    phase_id INT,
    start DATETIME,
    stop DATETIME
);

CREATE TABLE item_rate (
    id INTEGER PRIMARY KEY, 
    description TEXT DEFAULT 'New Item Rate',
    fee_per_hour FLOAT DEFAULT '0.00',
    archived INTEGER DEFAULT 0
);
CREATE TABLE item_type (
    id INTEGER PRIMARY KEY, 
    description TEXT DEFAULT 'New Item Type',
    archived INTEGER DEFAULT 0
);

CREATE TABLE project (
    id INTEGER PRIMARY KEY, 
    office_serial TEXT,
    tt_number INTEGER,
    user_id INTEGER,
    description TEXT,
    notes TEXT,
    status_id INTEGER
);

CREATE TABLE project_status (
    id INTEGER PRIMARY KEY,
    description TEXT,
    archived INTEGER DEFAULT 0
);


CREATE TABLE phase (
    id INTEGER PRIMARY KEY, 
    project_id INTEGER,
    number INTEGER,
    archived INTEGER DEFAULT 0
);

CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    name TEXT,
    password TEXT,
    usergroup_id INTEGER,
    email TEXT,
    archived INTEGER DEFAULT 0
);

CREATE TABLE usergroup (
    id INTEGER PRIMARY KEY,
    name TEXT,
    archived INTEGER DEFAULT 0
);

CREATE TABLE permission (
    id INTEGER PRIMARY KEY,
    url TEXT
);

CREATE TABLE usergroup_permission_tie (
    id INTEGER PRIMARY KEY,
    usergroup_id INTEGER,
    permission_id INTEGER
);

CREATE TABLE online_users (
    user_id INTEGER,
    session_id TEXT,
    time_record_id INTEGER,
    viewing_project_id INTEGER
);

/* user groups, privileges etc*/
    
INSERT into usergroup (id, name)
    VALUES (null, 'Admin');

INSERT into usergroup (id, name)
    VALUES (null, 'General');
    
INSERT into permission (id, url)
    VALUES (null, '/admin');
    
INSERT into permission (id, url)
    VALUES (null, '/my_projects');
    
INSERT into permission (id, url)
    VALUES (null, '/profile');
    
/* non-admin ties will be limited for test purposes */

INSERT into usergroup_permission_tie (id, usergroup_id, permission_id)
    VALUES (null, 1, 1);

INSERT into usergroup_permission_tie (id, usergroup_id, permission_id)
    VALUES (null, 1, 2);

INSERT into usergroup_permission_tie (id, usergroup_id, permission_id)
    VALUES (null, 1, 3);

INSERT into usergroup_permission_tie (id, usergroup_id, permission_id)
    VALUES (null, 2, 2);

INSERT into usergroup_permission_tie (id, usergroup_id, permission_id)
    VALUES (null, 2, 3);



/* to test features */

INSERT into user (id, name, password, usergroup_id, email) 
    VALUES (null, "Luke", "password", 1, "luke@macpractice.com");
    
INSERT into user (id, name, password, usergroup_id, email)
    VALUES (null, "Stick", "admin", 2, "luke@macpractice.com");
    
INSERT INTO user (id, name, password, usergroup_id, email)
    VALUES (null, "Mark", "comeoriginal", 1, "markhoefler@macpractice.com");
    
INSERT INTO user (id, name, password, usergroup_id, email)
    VALUES (null, "Roger", "roostermold", 1, "roger@macpratice.com");
    

/* test statuses */

INSERT into project_status (id, description)
    VALUES (null, 'Closed');

INSERT into project_status (id, description)
    VALUES (null, 'Open');
    
/* test types and rates */

INSERT into item_rate (id, description, fee_per_hour)
    VALUES (null, "Shared Rate", 75.00);
    
INSERT into item_rate (id, description, fee_per_hour)
    VALUES (null, "Non-Shared Rate", 150);

INSERT INTO item_type (id, description)
    VALUES (null, "Clipboard");
    
INSERT INTO item_type (id, description)
    VALUES (null, "EHR");
    
INSERT INTO item_type (id, description)
    VALUES (null, "Accounting");
    
/* project + items for Luke user*/

INSERT into project (id, tt_number, user_id, description, notes, status_id) 
    VALUES (null, null, 1, "Example Project", "Test notes for the project", 2);
    
INSERT into action_item (id, name, project_id, rate_id, type_id)
    VALUES (null, "Some Form", 1, 1, 1);    

INSERT into action_item (id, name, project_id, rate_id, type_id)
    VALUES (null, "Revisions", 1, 2, 2);
        
INSERT into action_item (id, name, project_id, rate_id, type_id)
    VALUES (null, "Level 3 Diagnostic", 1, 2, 1);  
    
/* 2nd project */
    
INSERT into project (id, tt_number, user_id, description, notes, status_id) 
    VALUES (null, null, 1, "Third Project", "Foo bar baz eggs spam", 2);
    
INSERT into action_item (id, name, project_id, rate_id, type_id)
    VALUES (null, "Elephant Hashes", 3, 1, 2); 
     
/* project + items for Stick user */
    
INSERT into project (id, tt_number, user_id, description, notes, status_id) 
    VALUES (null, null, 2, "Stick Project", "If Luke can see this, run away", 2);
     
INSERT into action_item (id, name, project_id, rate_id, type_id)
    VALUES (null, "Some Other Thing", 2, 2, 1);  