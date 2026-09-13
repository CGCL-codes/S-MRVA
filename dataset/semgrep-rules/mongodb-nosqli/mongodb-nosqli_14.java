
package testcode.sqli;

import com.mongodb.BasicDBObject;
import com.mongodb.BasicDBObjectBuilder;

public class ContactsService {

  private MongoDatabase db = MongoClientUtil.mongoClient.getDatabase("test");
  private MongoCollection<Document> collection = db.getCollection("contacts");

  public ArrayList<Document> basicDBObjectConstructorMap(String userName, String email) {
    HashMap<String, String> paramMap = new HashMap<>();
    // ok: mongodb-nosqli
    paramMap.put("sharedWith", userName);
    paramMap.put("email", email);
    BasicDBObject query = new BasicDBObject(paramMap);

    MongoCursor<Document> cursor = collection.find(query).iterator();
    ArrayList<Document> results = new ArrayList<>();
    while (cursor.hasNext()) {
      Document doc = cursor.next();
      results.add(doc);
    }

    return results;
  }
}
