# Script to generate the xml files for repo

import os
import sys
import xml.etree.ElementTree

def get_repo_value(repo_dir, key):
  repo_file = os.path.join(repo_dir, 'addons.xml') 
  try:
    tree = xml.etree.ElementTree.parse(repo_file)
    root = tree.getroot()
    returnValue = ''
    for addon in root.findall('addon'):
      repoProviderName = addon.get('provider-name')
      returnValue = addon.get(key)
      if 'netxeon-contry' == repoProviderName:
        break
    print repoProviderName
    return returnValue
  except Exception as e:
    print 'Failed to open %s' % repo_file
    print e.message
    sys.exit(1)

def main():
  # addon list
  dirs = (os.listdir('.'))
  # final addons text
  repoMap_xml = u"<repos>\n"
  # loop thru and add each addons addon.xml file
  for repo_dir in dirs:
    try:
      if(not os.path.isdir(repo_dir)):
        continue
      if(repo_dir.startswith('.')):
        # skip hidden dirs
        continue
      if(repo_dir == "tools"):
        # skip download directory
        continue
      repo_xml=""
      repo_xml += "<repo name=\"" + get_repo_value(repo_dir, "name") + "\"\n"
      repo_xml += "      id=\"" +  get_repo_value(repo_dir, "id") + "\"\n"
      repo_xml += "      version=\"" +get_repo_value(repo_dir, "version")+"\"\n"
      repo_xml += "      path=\"https://raw.githubusercontent.com/tustxk/AddOnRepo/master/" + get_repo_value(repo_dir, "name") + "/" + get_repo_value(repo_dir, "id") + "/" + get_repo_value(repo_dir, "id") + "-" + get_repo_value(repo_dir, "version") + ".zip" + "\"/>\n"
      repoMap_xml += repo_xml.rstrip() + u"\n"
    except Exception, e:
      # missing or poorly formatted addon.xml
      print "Failed to add xml"
      sys.exit(1)
  # clean and add closing tag
  repoMap_xml = repoMap_xml.strip() + u"\n</repos>\n"
  # save file
  try:
    # write data to the file
    open( "repoMap.xml", "w" ).write( repoMap_xml.encode( "UTF-8" ) )
    print "repoMap.xml generated!!!"
    sys.exit(0)
  except Exception, e:
    # oops
    print "An error occurred saving %s file!\n%s" % ( "RepoMap.xml", e, )
    sys.exit(1)


if __name__ == '__main__':
  main()
