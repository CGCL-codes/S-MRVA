
package testcode.sqli;

import com.mongodb.BasicDBObject;
import com.mongodb.BasicDBObjectBuilder;

public class ContactsService {

  private MongoDatabase db = MongoClientUtil.mongoClient.getDatabase("test");
  private MongoCollection<Document> collection = db.getCollection("contacts");

  public ArrayList<Document> basicDBObjectParse(String userName, String email) {
    HashMap<String, String> paramMap = new HashMap<>();
    // ruleid: mongodb-nosqli
    paramMap.put("$where", "this.sharedWith == \"" + userName + "\" && this.email == \"" + email + "\"");
    String json = new JSONObject(paramMap).toString();
    BasicDBObject query = new BasicDBObject().parse(json);

    MongoCursor<Document> cursor = collection.find(query).iterator();

    ArrayList<Document> results = new ArrayList<>();
    while (cursor.hasNext()) {
      Document doc = cursor.next();
      results.add(doc);
    }

    return results;
  }
}
