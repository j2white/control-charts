# bring in all the modules we will be using
import matplotlib
matplotlib.use('agg')
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import cx_Oracle

connect to the database
with cx_Oracle.connect('userid/pass@domain') as con:
    con.autocommit = True
    cur = con.cursor()
    cur.execute(""" ALTER session set nls_date_format = 'yyyy-mm-dd hh24:mi:ss' """)


# generic sql statement to retrive last 40 loads
# pandas can do it for me but i'll compute the 
# stdv, mean, upper limit, in the sql
# output the results to csv
sql = """
WITH
------------------------------------------------
base as (
        select
        trunc(load_dte) as load_dte,
        count(*) as ref_cnt
        from
        some_tbl
        where
        trunc(load_dte) >= trunc(sysdate) - 40
        group by
        trunc(load_dte)
        order by
        load_dte desc
        ),
------------------------------------------------
stdv_val as (
            select 
            round(stddev(x.ref_cnt),2) as stdv 
            from base x
            ),
------------------------------------------------
mean_val as (
            select 
            round(avg(xx.ref_cnt),2) as mean 
            from base xx
            )
------------------------------------------------
select
b.load_dte,
b.ref_cnt,
s.stdv as stdv,
m.mean,
m.mean - (s.stdv * 1) as lcl,
m.mean + (s.stdv * 1) as ucl

from
base b,
stdv_val s,
mean_val m

order by
1 desc
"""

def generate_data(run='y'):
	# if you want to get new data, execute the sql, if not read the csv
	if run == 'y':
		print('generating new data')
		df = pd.read_sql_query(sql,con)
		df.to_csv('control_chart_data.csv', header=True, index=False)
	else:
		print('using old data')
		df = pd.read_csv('control_chart_data.csv')
	return df

df = generate_data(run='y')

# let's take a look at our df
print(df.head())

# make sure that our date value is identified as a date
# assign our values to variables so we can bake them into an email
t = df['LOAD_DTE'] = pd.to_datetime(df['LOAD_DTE'])
c = df['REF_CNT']
s = df['STDV']
m = df['MEAN']
l = df['LCL']
u = df['UCL']

plt.plot(t, c, marker='o', markerfacecolor='blue', markersize=3, color='skyblue', linewidth=2, label='Referal Count')
plt.plot(t, m, color='b', label='Mean')
plt.plot(t, l, marker='', color='red', linewidth=2, label='Lower Control Limit')
plt.plot(t, u, marker='', color='red', linewidth=2, label='Upper Control Limit')
plt.legend()

# take a look at our plot and output it to .png
plt.show()
plt.savefig('Ref_Control_Chart.png')


# setup the message
mess_base = """
<!DOCTYPE html>
<html>
<body>
The control chart is based on the prior 40 loads.<br>
Today's referral count is: {c}.<br>
The mean referral count is: {m}.<br>
The standard deviation is: {st}.<br>
The lower control limit is: {l}.<br>
The upper control limit is: {u}.
</body>
</html>
"""
message = mess_base.format(c=c.head(1)[0],m=m.head(1)[0],st=s.head(1)[0],l=l.head(1)[0],u=u.head(1)[0])

def email_results(run='y'):
	import smtplib
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText
	from email.mime.image import MIMEImage

	attachment = 'Ref_Control_Chart.png'
	sender = """ first.last@gmail.com """
	distro_list = """ first.las@gmail.com, person.one@gmail.com, person.two@gmail """

	SERVER = 'localhost'
	msg = MIMEMultipart()
	msg["To"] = str(distro_list)
	msg["From"] = 'first.last@gmail.com'
	msg["Subject"] = 'Referral Daily Control Chart'
	body = message

	msgText = MIMEText('<b>%s</b><br><img src="cid:%s"><br>' % (body, attachment), 'html')  
	msg.attach(msgText)

	fp = open(attachment, 'rb')                                                    
	img = MIMEImage(fp.read())
	fp.close()
	img.add_header('Content-ID', '<{}>'.format(attachment))
	msg.attach(img)
	s = smtplib.SMTP(SERVER)

	if run =='y':
		s.sendmail(sender, distro_list.split(','), msg.as_string())
		exit(0)
	else:
		pass

email_results(run='y')


cur.close()
con.close()
