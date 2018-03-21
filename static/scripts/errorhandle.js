/**
 * Super, super basic error handling for the whole site.
 * This basically just sets up jQuery's AJAX calls to recognize
 * two response types - 401 (need to login) and 500 (every other error)
 * and bring up the browser's builtin popup to display the message the
 * server returns.
 */

$(document).ready(function(){
    $.ajaxSetup({        
        statusCode: {
            401: function(xhr, s, t){
                alert('You have been logged out. Returning to login screen.');
                window.location.replace('/login');
                return false;
            },
            
            500: function(xhr, s, t) {
                alert(xhr.responseText);
                return false;
            }
        }
    });
});