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