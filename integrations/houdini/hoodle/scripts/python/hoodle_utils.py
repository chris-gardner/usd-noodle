import hou


def get_noodle_instance():
    # search through all the pane tabs to get an existing instance of noodle
    for panetab in hou.ui.paneTabs():
        if panetab.type() == hou.paneTabType.PythonPanel:
            interface = panetab.activeInterface()
            if interface.name() == 'usd_noodle':
                noodle_widget = panetab.activeInterfaceRootWidget()
                if not panetab.isCurrentTab():
                    panetab.setIsCurrentTab()
                return noodle_widget
    
    # sooo, no dice. we need to create one
    
    # if we're in the solaris desktop. create a new noodle tab where the SceneGraphDetails panel goes
    desktop = hou.ui.curDesktop()
    if desktop.name() == 'Solaris':
        panels = [x for x in desktop.paneTabs() if x.type() == hou.paneTabType.PythonPanel]
        panels = [x for x in panels if x.activeInterface().name() == 'SceneGraphDetails']
        if panels:
            poo = panels[0]
            pytype = hou.pypanel.interfaces()['usd_noodle']
            pypanel = poo.pane().createTab(hou.paneTabType.PythonPanel)
            pypanel.setActiveInterface(pytype)
            noodle_widget = pypanel.activeInterfaceRootWidget()
            return noodle_widget
    
    # annnnd finally, create a floating tab
    pypanel = desktop.createFloatingPaneTab(hou.paneTabType.PythonPanel, python_panel_interface='usd_noodle')
    noodle_widget = pypanel.activeInterfaceRootWidget()
    return noodle_widget
