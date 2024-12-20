from flask import Flask, request, render_template, redirect, url_for, flash
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
import redis
import base64
import smtplib
from email.mime.text import MIMEText
from config import Config
import secrets
import string

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Redis
r = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], password=app.config['REDIS_PASSWORD'], decode_responses=True)

# Index Route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        cn = search_ad_user(email)
        if cn:
            encoded_cn = base64.b64encode(cn.encode()).decode()
            r.setex(email, 3600, encoded_cn)  # Save to Redis with TTL of 60 minutes
            send_reset_email(email)
            flash('重制链接已发送至邮箱: [' + email + ']，请查收，链接60分钟后失效', 'success')
        else:
            flash('用户不存在', 'danger')
    return render_template('index.html')


def generate_random_string(length=16):
    # Define the alphabet: lowercase, uppercase letters, digits, and special characters
    alphabet = string.ascii_letters + string.digits + string.punctuation

    # Generate a random string using the secrets module for cryptographic security
    random_string = ''.join(secrets.choice(alphabet) for _ in range(length))

    return random_string

def search_ad_user(email):
    server = Server(app.config['LDAP_SERVER'], get_info=ALL, use_ssl=True)
    conn = Connection(server, user=app.config['LDAP_USER'], password=app.config['LDAP_PASSWORD'], authentication='SIMPLE', auto_bind=True)
    # basedn, such as 'DC=your-company,DC=com'
    # email: attribute in AD 
    # distinguishedName: user's full DN
    conn.search(basedn, f'(email={email})', attributes=['distinguishedName'])
    if conn.entries:
        return conn.entries[0].distinguishedName.value
    conn.unbind()
    return None

def send_reset_email(email):
    params = generate_random_string(64)
    r.setex(params, 3600, email)  # 设置60分钟的ttl
    reset_url = url_for('resetpwd', p=params, _external=True)
    msg = MIMEText(f"使用如下链接重置密码:【{reset_url}】，链接60内分钟有效！")
    msg['Subject'] = 'Windows AD 密码重置'
    msg['From'] = app.config['SMTP_USER']
    msg['To'] = email
    with smtplib.SMTP(app.config['SMTP_HOST'], app.config['SMTP_PORT']) as server:
        server.starttls()
        server.login(app.config['SMTP_USER'], app.config['SMTP_PASSWORD'])
        server.sendmail(app.config['SMTP_USER'], email, msg.as_string())

# Reset Password Route
@app.route('/resetpwd', methods=['GET', 'POST'])
def resetpwd():
    params = request.args.get('p')
    if not params:
        return "无效的请求", 400
    try:
        email = r.get(params)
        search_user_dn = r.get(email)
        if not search_user_dn:
            return "链接过期或已失效，请联系管理员！ Oops", 400
    except Exception as ex:
        print('链接失效啦～', ex)
        flash('链接过期或已失效，请联系管理员！', 'danger')

    if request.method == 'POST':
        new_password = request.form['password']
        try:
            if change_ad_password(email, new_password, search_user_dn):
                r.delete(params)
                r.delete(email)
                flash('密码修改成功', 'success')
                return redirect(url_for('index'))
            else:
                flash('密码修改失败，请提高密码复杂度！', 'danger')
        except Exception as ex:
            print('链接失效啦～', ex)
            flash('重置链接过期或已失效，请联系管理员！', 'danger')

    return render_template('resetpwd.html', email=email)

def change_ad_password(email, new_password, search_user_dn):
    dn = base64.b64decode(search_user_dn).decode()
    server = Server(app.config['LDAP_SERVER'], get_info=ALL, use_ssl=True)
    conn = Connection(server, user=app.config['LDAP_USER'], password=app.config['LDAP_PASSWORD'], auto_bind=True)
    conn.modify(dn, {'unicodePwd': [(MODIFY_REPLACE, [('"{}"'.format(new_password)).encode('utf-16-le')])]})
    return conn.result['result'] == 0

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)
