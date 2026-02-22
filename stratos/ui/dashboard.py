from stratos.ui.controllers.launch_controller import StratosDashboard

def main(cli_args=None):
    ui = StratosDashboard(cli_args)
    ui.run()

if __name__ == "__main__":
    main()
