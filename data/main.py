from .control import Control

def main(size):
    app = Control(size)
    app.run()


if __name__ == '__main__':
    main((800,500))
