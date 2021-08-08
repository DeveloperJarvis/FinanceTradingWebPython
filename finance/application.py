import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


def isUserNameProvided():
    if not request.form.get("username"):
        return apology("must provide username", 403)

def isPasswordProvided():
    if not request.form.get("password"):
        return apology("must provide password", 403)


#TODO1
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
#    return apology("TODO")


#TODO2
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

         # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation password", 403)
        # Ensure password and confirmation were a match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirm password fields do not match", 403)

        # Query database for username
        try:
            rows = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                            username = request.form.get("username"),
                            hash = generate_password_hash(request.form.get("password")))
        except:
            return apology("username already exists", 403)
        # Ensure username exists and password is correct
#        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
#            return apology("invalid username and/or password", 403)
        if rows is None:
            return apology("registration error", 403)
            # TODO: write code...
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("register.html")
#    return apology("TODO")


#TODO3
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Ensure a symbol was provided
        if not request.form.get("symbol"):
            return apology("must provide Stock Symbol", 403)

        # converts symbol to uppercase
        symbol = request.form.get("symbol").upper()

        #searches for symbol
        stock = lookup(symbol)

        #checks if stock exist or not else return apology
        if stock is None:
            return apology("invalid symbol", 400)

        stock['price'] = usd(stock['price'])
        #redirects to quoted page with attributes including name, symbol and price
        return render_template("quoted.html", stock = stock)
    else:
        return render_template("quote.html")
#    return apology("TODO")


#TODO4
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Ensure a symbol was provided
        if not request.form.get("symbol"):
            return apology("must provide Stock Symbol", 403)
        # Ensure a shares are provided was provided
        elif not request.form.get("shares"):
            return apology("must provide share count you need to purchase", 403)
        # Ensure a shares are provided was provided is not floating
        elif not request.form.get("shares").isdigit():
            return apology("must provide valid share number", 403)

        # converts symbol to uppercase
        symbol = request.form.get("symbol").upper()

        # saves amount of shares in integers
        shares = int(request.form.get("shares"))

        #searches for symbol
        stock = lookup(symbol)

        #checks if stock exist or not else return apology
        if stock is None:
            return apology("invalid symbol", 400)

        #fetch cash for the specific user whose session is going on
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        cash = rows[0]["cash"]

        #calculate updated cash after buying stocks
        updated_cash = cash - shares * stock['price']
        # check if user has new cash which is not less than 0
        if updated_cash < 0:
            return apology("can't afford", 400)

        #update the database table 'users'
        db.execute("UPDATE users SET cash = :updated_cash WHERE id = :id",
                    updated_cash = updated_cash,
                    id = session["user_id"])

        # update the database table 'transactions'
        db.execute("""
            INSERT INTO transactions
                    (user_id, symbol, shares, price)
            VALUES (:user_id, :symbol, :shares, :price)
            """,
        user_id = session["user_id"],
        symbol = stock["symbol"],
        shares = shares,
        price = stock["price"])

        # prints out flash on the browser
        flash("Bought!")

        #after buying redirect to buy
        return redirect("/")
    else:
        return render_template("buy.html")
#    return apology("TODO")


#TODO5
@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    #fetch symbol and sum of shares from transaction table in database only if total shares per stock is greater than zero for current user only
    rows = db.execute("""
        SELECT symbol, SUM(shares) as totalShares
        FROM transactions
        WHERE user_id = :user_id
        GROUP BY symbol
        HAVING totalShares > 0;
    """,
    user_id = session["user_id"])

    if rows is None:
            return apology("No record found", 400)


    #declaration of holdings as dictionary to hold detail
    holdings = []
    #declaration of grand total as integer
    grand_total = 0

    #searching in rows and appending data to holdings one by one
    # at the end calculating the grand total
    for row in rows:
        stock = lookup(row["symbol"])
        holdings.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "shares": row["totalShares"],
            "price": usd(stock["price"]),
            "total": usd(stock["price"] * row["totalShares"])
        })
        grand_total += stock["price"] * row["totalShares"]

    #fetch cash for the specific user whose session is going on
    rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
    cash = rows[0]["cash"]

    #adding cash to the grandtotal
    grand_total += cash

    #calling html file to display all holdings and cash in usd and grand total in usd
    return render_template("index.html", holdings = holdings, cash = usd(cash), grand_total = usd(grand_total))
#    return apology("TODO")


#TODO6
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # Ensure a symbol was provided
        if not request.form.get("symbol"):
            return apology("must provide Stock Symbol", 403)
        # Ensure a shares are provided was provided
        elif not request.form.get("shares"):
            return apology("must provide share count you need to purchase", 403)
        # Ensure a shares are provided was provided is not floating
        elif not request.form.get("shares").isdigit():
            return apology("must provide valid share number", 403)

        # converts symbol to uppercase
        symbol = request.form.get("symbol").upper()

        # saves amount of shares in integers
        shares = int(request.form.get("shares"))

        #searches for symbol
        stock = lookup(symbol)

        #checks if stock exist or not else return apology
        if stock is None:
            return apology("invalid symbol", 400)

        #fetch symbol and sum of shares from transaction table in database only if total shares per stock is greater than zero for current user only
        rows = db.execute("""
            SELECT symbol, SUM(shares) as totalShares
            FROM transactions
            WHERE user_id = :user_id
            GROUP BY symbol
            HAVING totalShares > 0;
        """,
        user_id = session["user_id"])
        print("going")
        for row in rows:
            if row["symbol"] == symbol:
                if shares > row["totalShares"]:
                    return apology("You do not have that many shares", 403)

        #fetch cash for the specific user whose session is going on
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        cash = rows[0]["cash"]

        #calculate updated cash after buying stocks
        updated_cash = cash + shares * stock['price']
        # check if user has new cash which is not less than 0
        #if updated_cash < 0:
        #    return apology("can't afford", 400)

        #update the database table 'users'
        db.execute("UPDATE users SET cash = :updated_cash WHERE id = :id",
                    updated_cash = updated_cash,
                    id = session["user_id"])

        # update the database table 'transactions'
        db.execute("""INSERT INTO transactions
                (user_id, symbol, shares, price)
            VALUES (:user_id, :symbol, :shares, :price)
        """,
        user_id = session["user_id"],
        symbol = stock["symbol"],
        shares = -1 * shares,
        price = stock["price"])

        # prints out flash on the browser
        flash("Sold!")

        #after buying redirect to buy
        return redirect("/")
    else:
        #fetch symbol and sum of shares from transaction table in database only if total shares per stock is greater than zero for current user only
        rows = db.execute("""
            SELECT symbol
            FROM transactions
            WHERE user_id = :user_id
            GROUP BY symbol
            HAVING SUM(shares) > 0;
        """,
        user_id = session["user_id"])

        return render_template("sell.html", symbols =[ row["symbol"] for row in rows ])
#    return apology("TODO")


#TODO7
@app.route("/history")
@login_required
def history():

    """Show history of transactions"""
    #fetch all transaction history for current user
    transactions = db.execute("""
        SELECT symbol, shares, price, transacted
        FROM transactions
        WHERE user_id = :user_id
    """,
    user_id = session["user_id"])

    # converting price to USD price for transactions
    for i in range(len(transactions)):
        transactions[i]["price"] = usd(transactions[i]["price"])

#    return render_template("history.html")
    return render_template("history.html", transactions=transactions)
#    return apology("TODO")


#TODO8
@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":
        # Ensure a amount of cash is provided
        if not request.form.get("cash"):
            return apology("must provide amount of cash to add", 403)
        # Ensure a shares are provided was provided is not floating
        elif not request.form.get("cash").isdigit():
            return apology("must provide cash in multiple of 1 dollar", 403)

        # declaration of amount provided by the user
#        amount = request.form.get("cash")

        #fetch cash for the specific user whose session is going on
##        rows = db.execute("UPDATE cash FROM users WHERE id = :_id", id = session["user_id"])
   #     cash = rows[0]["cash"]

        #calculate updated cash after buying stocks
  #      updated_cash = cash + request.form.get("cash")
        # check if user has new cash which is not less than 0
        #if updated_cash < 0:
        #    return apology("can't afford", 400)

        #update the database table 'users'
        db.execute("""UPDATE users
                    SET cash = cash + :updated_cash
                    WHERE id = :user_id""",
                    updated_cash = request.form.get("cash"),
                    user_id = session["user_id"])
        #shouts cash has been added to the user
        flash("Cash added!..")
        #redirects to portfolio
        return redirect("/")
    else:
        return render_template ("addcash.html")
#    return apology("TODO")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
