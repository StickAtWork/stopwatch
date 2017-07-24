import smtplib

from email.mime.multipart import MIMEMultipart
from email.message import Message
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText

def email_invoice(user_email, invoice, cc_email=None):
    """Sends email with the invoice as attachment.
    
    The default for this will eventually be 
        FROM: invoice@stopwatch.com
        TO: accounting@macpractice.com
        SUBJECT: whatever accounting wants to see
        
        Body: some default message for accounting
        Attachment: the invoice
        
    """
    
    me = "invoice@stopwatch.com"
    you = user_email
    
    msg = MIMEMultipart()
    msg['Subject'] = "Testing"
    msg['From'] = me
    msg['To'] = you
    if cc_email is not None:
        msg['Cc'] = cc_email
        recips = [you, cc_email]
    else:
        recips = you
    
    text = Message()
    
    text.set_payload("""
    This is a test of the Stopwatch Invoice System. 
    
    Eventually this invoice will go to Accounting, for now it is going to you. 
    """)
    msg.attach(text)
    
    # preps invoice to be an attachment
    the_invoice = MIMEBase('application', 'octet-stream')
    the_invoice.set_payload(invoice)
    the_invoice.add_header(
                        'Content-Disposition', 
                        'attachment', 
                        filename="invoice.html"
                    )
    msg.attach(the_invoice)
    
    s = smtplib.SMTP('smtp.macpractice.com')
    s.sendmail(me, recips, msg.as_string())
    s.quit()
    
def email_new_password(user_email, username, password):
    """Informs the user that their password has been changed.
    
    At present (07/19/17) this is just called when a user is created
    or when an admin presses "Reset Password" in the Admin tab.
    
    There is no CC on this email (at present) because the idea is
    nobody else sees the password except for the actual user.
    """
    me = "mcp@stopwatch.com"
    you = user_email
    
    msg = MIMEMultipart()
    msg['Subject'] = "New Password"
    msg['From'] = me
    msg['To'] = you
    
    text = Message()
    
    text.set_payload("""
    Hey,
    
    Your Stopwatch password was changed.
    
    Your username is: {}
    Your password is: {}
    
    If you received this message in error, contact an admin.
    """.format(username, password))
    
    msg.attach(text)
    
    s = smtplib.SMTP('smtp.macpractice.com')
    s.sendmail(me, you, msg.as_string())
    s.quit()