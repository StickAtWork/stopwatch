/**
 * Sets up our hidden popup window to respond to custom
 * event "appear" and to re-hide itself when dismissed.
 * 
 * Make sure to pass the actual desired content of the
 * popup window in an array. Example:
 *
 *    $('#popup-window').trigger('appear', [myPopupContentHere])
 */
$(document).ready(function(){
    
    //custom event
    $('#popup-window').on('appear', function(e, info){
        $('#popup-window .content').html(info);
        $('#popup-bg').removeClass('hidden');
        return false;
    });
    
    //dismisses the window
    $('#popup-window #popup-close').on('click', function(){
        $('#popup-window .content').empty();
        $('#popup-bg').addClass('hidden');
        return false;
    });
});