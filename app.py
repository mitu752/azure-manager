import threading
from flask import Flask, render_template, request, url_for, redirect, flash, make_response,session,jsonify
import function
from flask_sqlalchemy import SQLAlchemy
import os
import re

defaultadmin ='admin'
defaultpass = 'admin'

app = Flask(__name__)
app.jinja_env.filters['zip'] = zip
# 请将 xxx 替换为随机字符
app.config['SECRET_KEY'] = os.environ.get('random_key','c2jf932hibfiuebvwievubheriuvberv')


DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///flask_app.db')
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)



class User(db.Model):

  account = db.Column(db.String(100),primary_key=True)
  client_id = db.Column(db.String(100))
  client_secret = db.Column(db.String(100))
  tenant_id = db.Column(db.String(100))
  subscription_id = db.Column(db.String(100))

  def __init__(self, account, client_id,client_secret,tenant_id,subscription_id):
    self.account = account
    self.client_id = client_id
    self.client_secret = client_secret
    self.tenant_id = tenant_id
    self.subscription_id = subscription_id







@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #logger.debug("login post method")

        username = request.form['userName']
        password = request.form['passWord']

        if username == os.environ.get('adminname',defaultadmin) and password == os.environ.get('adminpassword',defaultpass):
        #if username == 'adminusername' and password == 'adminpassword':

            session['username'] = username
            session['password'] = password
            resp = make_response(render_template('index.html', users=User.query.all()))
            resp.set_cookie('username', username)
            return resp
            #return jsonify({'status': '0', 'errmsg': 'login success!'})
        else:
            # return redirect(url_for('error'))
            return jsonify({'status': '-1', 'errmsg': 'error account!'})

    #logger.debug("login get method")
    return render_template('login.html')


@app.route('/', methods=['GET', 'POST'])
def index():
    #logger.debug("index page")
    #logger.debug("cookie name %s" % request.cookies.get('username'))

    if 'username' in session:
        #logger.debug("login user is %s" % flask_login.current_user)
        #logger.debug('Logged in as %s' % escape(session['username']))
        return render_template('index.html',  users=User.query.all())
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))










@app.route('/account/add', methods=['GET', 'POST'])
def accountadd():
    if 'username' in session:
        if request.method == 'POST':  # 判断是否是 POST 请求
            # 获取表单数据
            account = request.form.get('account')
            client_id = request.form.get('client_id')
            client_secret = request.form.get('client_secret')
            tenant_id = request.form.get('tenant_id')
            subscription_id = request.form.get('subscription_id')
            # 验证数据
            if not account or not client_id or not client_secret or not tenant_id or not subscription_id:
                flash('输入错误')  # 显示错误提示
                return redirect(url_for('index'))  # 重定向回主页
            # 保存表单数据到cookie
            u = User(account, client_id,client_secret,tenant_id,subscription_id)
            db.session.add(u)
            db.session.commit()

            resp = make_response(redirect(url_for('index')))

            flash('添加管理账户成功')
            return resp

        return render_template('account.html')
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))

@app.route('/account/delete')
def accountdel():
    if 'username' in session:
        account = request.args.get('account')


        dele = User.query.filter(User.account == account).first()
        db.session.delete(dele)
        db.session.commit()





        flash('删除账户成功')
        resp = make_response(redirect(url_for('index')))
        return resp
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))


@app.route('/account/list')
def list():
    if 'username' in session:
        account = request.args.get('account')
        result = User.query.filter(User.account == account).all()

        client_id = result[0].client_id
        client_secret = result[0].client_secret
        tenant_id = result[0].tenant_id
        subscription_id = result[0].subscription_id

        credential = function.create_credential_object(tenant_id, client_id, client_secret)

        dict, subscription_list = function.list(subscription_id, credential)
        return render_template('list.html',dict=dict, subscription_list=subscription_list, account=account)
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))


@app.route('/account/vm/create', methods=['GET', 'POST'])
def create_vm():
    if 'username' in session:
        account = request.args.get('account')
        print(account)

        if request.method == 'POST':
            result = User.query.filter(User.account == account).all()

            client_id = result[0].client_id
            client_secret = result[0].client_secret
            tenant_id = result[0].tenant_id
            subscription_id = result[0].subscription_id



            credential = function.create_credential_object(tenant_id, client_id, client_secret)
            tag = request.form.get('tag')
            location = request.form.get('location')
            size = request.form.get('size')
            os = request.form.get('os')
            set = request.form.get('set')
            rootpwd=request.form.get('rootpwd')
            storgesize=request.form.get('storgesize')
            ## 此处为VM默认登陆密码

            username = request.form.get('vmusername')#"defaultuser"
            password = request.form.get('vmpasswd')#"Thisisyour.password1"

            char = re.findall(r'[a-z]', password)
            bigchar = re.findall(r'[A-Z]', password)
            num = re.findall(r'[0-9]', password)
            if len(num) * len(bigchar) * len(char) == 0 or len(password) < 12 or len(password) > 72:
                flash('VM密码不合规，请输入至少12位密码，且包含大小写字母和数字')
            else:
                for i in range(int(set)):
                    name = (tag + str(i + 1))
                    function.create_resource_group(subscription_id, credential, name, location)
                    threading.Thread(target=function.create_or_update_vm, args=(
                    subscription_id, credential, name, location, username, password, size, os,rootpwd,storgesize)).start()
                flash('创建中，请耐心等待VM创建完成，大约需要1-3分钟')



        return render_template('vm.html', account=account)
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))


@app.route('/account/vm/delete/<string:tag>')
def delete_vm(tag):
    if 'username' in session:
        account = request.args.get('account')
        result = User.query.filter(User.account == account).all()

        client_id = result[0].client_id
        client_secret = result[0].client_secret
        tenant_id = result[0].tenant_id
        subscription_id = result[0].subscription_id





        credential = function.create_credential_object(tenant_id, client_id, client_secret)
        threading.Thread(target=function.delete_vm, args=(subscription_id, credential, tag)).start()
        flash("删除中，请耐心等待1-3分钟")

        dict, subscription_list = function.list(subscription_id, credential)
        return render_template('list.html', dict=dict, subscription_list=subscription_list, account=account)
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))

@app.route('/account/vm/start/<string:tag>')
def start_vm(tag):
    if 'username' in session:
        account = request.args.get('account')

        result = User.query.filter(User.account == account).all()

        client_id = result[0].client_id
        client_secret = result[0].client_secret
        tenant_id = result[0].tenant_id
        subscription_id = result[0].subscription_id

        credential = function.create_credential_object(tenant_id, client_id, client_secret)
        threading.Thread(target=function.start_vm, args=(subscription_id, credential, tag)).start()
        flash("开机中，请耐心等待1-3分钟")
        dict, subscription_list = function.list(subscription_id, credential)
        return render_template('list.html', dict=dict, subscription_list=subscription_list, account=account)
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))

@app.route('/account/vm/stop/<string:tag>')
def stop_vm(tag):
    if 'username' in session:
        account = request.args.get('account')

        result = User.query.filter(User.account == account).all()

        client_id = result[0].client_id
        client_secret = result[0].client_secret
        tenant_id = result[0].tenant_id
        subscription_id = result[0].subscription_id


        credential = function.create_credential_object(tenant_id, client_id, client_secret)
        threading.Thread(target=function.stop_vm, args=(subscription_id, credential, tag)).start()
        flash("关机中，请耐心等待1-3分钟")
        dict, subscription_list = function.list(subscription_id, credential)
        return render_template('list.html', dict=dict, subscription_list=subscription_list, account=account)
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))

@app.route('/account/vm/changeip/<string:tag>')
def changeip_vm(tag):
    if 'username' in session:
        account = request.args.get('account')

        result = User.query.filter(User.account == account).all()

        client_id = result[0].client_id
        client_secret = result[0].client_secret
        tenant_id = result[0].tenant_id
        subscription_id = result[0].subscription_id


        credential = function.create_credential_object(tenant_id, client_id, client_secret)
        try:
            threading.Thread(target=function.change_ip, args=(subscription_id, credential, tag)).start()
            flash("更换IP进行中，请耐心等待1-3分钟")
            return redirect(url_for('index'))
        except:
            flash("出现未知错误，请重试")
    else:
        #logger.debug("you are not logged in")
        return redirect(url_for('login'))

if __name__ == '__main__':
    db.create_all()
    app.run()
