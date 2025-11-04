
class WaterTable:

    def __init__(self,g_i):
        self.g_i = g_i

    def CreateWaterLevel(self, points, waterLevelname):
        self.points = points
        self.waterLevelName = waterLevelname

        self.g_i.gotoflow()
        waterlevel_i = self.g_i.waterlevel(self.points)
        waterlevel_i.rename(self.waterLevelName)
    
    def setWaterLevel(self, soil, waterLevelName, phaseName):
        self.waterLevelName = waterLevelName
        self.phasename = phaseName
        self.soil = soil

        self.g_i.setwaterlevel((self.soil), (self.phasename), self.waterLevelName)
        

