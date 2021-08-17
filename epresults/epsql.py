import sys

epresults_location = r'A:\Files\PycharmProjects\RL-BCA\OpenStudio_Models\BEM_Custom\Base_Output\BEM_5z_Unitary_base_output\run'
sys.path.append(epresults_location)

import epresults as ep

pathtosim = epresults_location + r'\eplusout'  # do not include extensions
mysim = ep.load.epLoad(pathtosim)


available_tables = mysim.tables.avail_tabular()

ref = available_tables[available_tables.TableName == 'Site and Source Energy']
siteandsource = mysim.tables.get_tabular(ref)

availseries = mysim.sql.availseries()