
import org.springframework.context.ApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;
import org.springframework.core.io.Resource;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import org.springframework.web.bind.annotation.RequestParam;

public static void bad2(@RequestParam String filename)
{
    ApplicationContext appContext = 
       new ClassPathXmlApplicationContext(new String[] {"If-you-have-any.xml"});

    // ruleid: tainted-file-path
    Resource resource = appContext.getResource("classpath:com/" + filename);
            
    try {
       InputStream is = resource.getInputStream();
       BufferedReader br = new BufferedReader(new InputStreamReader(is));
            
       String line;
       while ((line = br.readLine()) != null) {
          System.out.println(line);
       } 
       br.close();
            
    } catch(IOException e){
       e.printStackTrace();
    }
}
