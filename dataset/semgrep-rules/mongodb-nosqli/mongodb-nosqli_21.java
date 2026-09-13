
package testcode.sqli;

import com.mongodb.BasicDBObject;
import com.mongodb.BasicDBObjectBuilder;

public class ContactsService {

  private MongoDatabase db = MongoClientUtil.mongoClient.getDatabase("test");
  private MongoCollection<Document> collection = db.getCollection("contacts");

  public ArrayList<Document> basicDBObjectBuilderAppend(String userName, String email) {
    // ruleid: mongodb-nosqli
    BasicDBObject query = (BasicDBObject) BasicDBObjectBuilder
        .start()
        .append("$where", "this.sharedWith == \"" + userName + "\" && this.email == \"" + email + "\"")
        .get();

    MongoCursor<Document> cursor = collection.find(query).iterator();

    ArrayList<Document> results = new ArrayList<>();
    while (cursor.hasNext()) {
      Document doc = cursor.next();
      results.add(doc);
    }

    return results;
  }
}
