import smtplib

from email.mime.multipart import MIMEMultipart
from email.message import Message
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText

def email_invoice(invoice, user_email, cc_email=None):
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
    #cc = "emr@macpractice.com"
    
    #recips = [you, cc]
    
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
    
    text.set_payload("This is a test of the Stopwatch Invoice System. \n\n")
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