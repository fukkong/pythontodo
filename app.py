from api import create_app

app = create_app()

if __name__ == "__main__":
    print('start app')
    app.run(port=5001, debug=True, threaded=True)
